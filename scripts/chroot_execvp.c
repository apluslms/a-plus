/**
 * Moves the target directory inside sandboxed system
 * and then runs the given command in it.
 *
 * @author Teemu Lehtinen
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <unistd.h>
#include <limits.h>
#include <dirent.h>
#include <fcntl.h>
#include <pwd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <sys/resource.h>

#define SANDBOX_DIR "/var/sandbox"
#define SANDBOX_UID 666
#define SANDBOX_NET_UID 667
#define CMD_PATH ".:/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/local/sandbox:/usr/local/sandbox/"
#define TMP_PATH "/tmp/grader"
#define KB_IN_BYTES 1024
#define MB_IN_BYTES 1048576
#define GB_IN_BYTES 1073741824

static void cleanup();
static void handle_signals(int sig);
static void connect_signals();
int fail(const char *at);
int limit_process(unsigned long int memory, unsigned long int files, unsigned long int disk);
unsigned long int parse_number(const char *argument);
int chown_directory(const char *dir, uid_t uid, gid_t gid);
int move_directory(const char *dir, const char *to);
int copy_directory(const char *dir, const char *to);
int copy_file(const char *file, const char *to);

static char* dir = NULL;
static char* path = NULL;
static uid_t orig_uid = 0;
static gid_t orig_gid = 0;
static pid_t pid = 0;
static unsigned int time_limit = 0;

int main(int argc, char *argv[])
{
	int argp = 1;
	uid_t uid = SANDBOX_UID;

	// Check the "net" argument.
	if (argc > argp && strcmp(argv[argp], "net") == 0)
	{
		uid = SANDBOX_NET_UID;
		argp = 2;
	}

	// Print usage.
	if (argc < 6 + argp)
	{
		printf("Runs a command in a sandbox environment.\n");
		printf("Usage: %s [net] time heap files disk dir course_key prg [arguments...]\n", argv[0]);
		printf("    1k for kilobyte, m for mega, g for giga and - for unlimited\n");
		printf("    net          enables network (optional)\n");
		printf("    time         maximum time for process in seconds\n");
		printf("    heap         maximum heap memory size\n");
		printf("    files        maximum number of open file descriptors\n");
		printf("    disk         maximum disk write size\n");
		printf("    dir          a target directory or -\n");
		printf("    course_key   a course key for building PATH\n");
		printf("    prg          a program to envoke\n");
		printf("    arguments    any arguments for program (optional)\n");
		return 0;
	}

	connect_signals();

	// Make static dir variable.
	dir = malloc(strlen(argv[argp + 4]) + 1);
	if (dir == NULL)
	{
		fprintf(stderr, "FAILED: malloc directory name\n");
		return fail("main");
	}
	strcpy(dir, argv[argp + 4]);
	if (strcmp(dir, "-") != 0)
	{
		if (access(dir, R_OK | W_OK | X_OK) != 0)
		{
			fprintf(stderr, "FAILED: access %s\n", dir);
			return fail("main");
		}
		char tmp_path[strlen(SANDBOX_DIR) + strlen(TMP_PATH) + 1];
		strcpy(tmp_path, SANDBOX_DIR);
		strcat(tmp_path, TMP_PATH);
		if (access(tmp_path, R_OK | W_OK | X_OK) != 0)
		{
			fprintf(stderr, "FAILED: access %s\n", tmp_path);
			return fail("main");
		}

		// Move target dir inside sandbox.
		path = tempnam(tmp_path, NULL);
		if (path == NULL)
		{
			fprintf(stderr, "FAILED: tempnam %s\n", tmp_path);
			return fail("main");
		}
		if (move_directory(dir, path) != 0)
		{
			fprintf(stderr, "FAILED: move %s %s\n", dir, path);
			return 1;
		}

		// Store directory owner.
		struct stat path_stat;
		if (lstat(path, &path_stat) != 0)
		{
			fprintf(stderr, "FAILED: stat %s\n", path);
			return fail("main");
		}
		orig_uid = path_stat.st_uid;
		orig_gid = path_stat.st_gid;

		// Change directory owner.
		if (chown_directory(path, uid, orig_gid) != 0)
		{
			fprintf(stderr, "FAILED: chown %s to %d\n", path, uid);
			return 1;
		}
	}

	// Prepare values before forking.
	char *local_path = TMP_PATH;
	if (path != NULL)
	{
		local_path = path + strlen(SANDBOX_DIR);
	}
	unsigned long int memory = parse_number(argv[argp + 1]);
	unsigned long int files = parse_number(argv[argp + 2]);
	unsigned long int disk = parse_number(argv[argp + 3]);
	char cmd_path[strlen(CMD_PATH) + strlen(argv[argp + 5]) + 1];
	strcpy(cmd_path, CMD_PATH);
	strcat(cmd_path, argv[argp + 5]);

	// Limit maximum run time.
	time_limit = parse_number(argv[argp]);
	if (time_limit > 0 && time_limit < ULONG_MAX) alarm(time_limit);

	// Fork child process.
	pid = fork();
	if (pid == -1)
	{
		fprintf(stderr, "FAILED: fork\n");
		return fail("main");
	}
	if (pid == 0)
	{
		if (chroot(SANDBOX_DIR) != 0)
		{
			fprintf(stderr, "FAILED: chroot %s\n", SANDBOX_DIR);
			return fail("main");
		}
		if (setuid(uid) != 0)
		{
			fprintf(stderr, "FAILED: setuid %d\n", uid);
			return fail("main");
		}
		if (chdir(local_path) != 0)
		{
			fprintf(stderr, "FAILED: chdir %s\n", local_path);
			return fail("main");
		}

		// Create command line array.
		char *cmd = argv[argp + 6];
		int argn = argp + 7;
		char *arg[argc - argn];
		arg[0] = cmd;
		int p = 1;
		while (argn < argc)
		{
			arg[p] = argv[argn];
			p++;
			argn++;
		}
		arg[p] = NULL;

		// Create environment array.
		char *env[4];
		char envpath[6 + strlen(cmd_path)];
		strcpy(envpath, "PATH=");
		strcat(envpath, cmd_path);
		env[0] = envpath;
		struct passwd *pw = getpwuid(uid);
		if (pw == NULL)
		{
			fprintf(stderr, "FAILED: getpwuid %d\n", uid);
			return fail("main");
		}
		char envhome[6 + strlen(pw->pw_dir)];
		strcpy(envhome, "HOME=");
		strcat(envhome, pw->pw_dir);
		env[1] = envhome;
		env[2] = "DISPLAY=:0";
		env[3] = NULL;

		if (limit_process(memory, files, disk) != 0) return 1;

		// Update path in current env for finding the cmd.
		if (setenv("PATH", cmd_path, 1) != 0)
		{
			fprintf(stderr, "FAILED: setenv PATH=%s\n", cmd_path);
			return fail("main");
		}

		// Replace the process.
		execvpe(cmd, arg, env);
		fprintf(stderr, "FAILED: execvp\n");
		return fail("main");
	}

	// Wait for child process to terminate.
	else
	{
		pid_t w;
		int status;
		do
		{
			w = waitpid(pid, &status, 0);
			if (w == -1)
			{
				fprintf(stderr, "FAILED: waitpid %d\n", pid);
				return fail("main");
			}
		}
		while (!WIFEXITED(status) && !WIFSIGNALED(status));
		cleanup();
		if (WIFEXITED(status))
		{
			return WEXITSTATUS(status);
		}
		fprintf(stderr, "FAILED: Process did not end with exit status.\n");
		return fail("main");
	}
}

static void cleanup()
{
	if (path != NULL)
	{
		if (orig_uid > 0)
		{
			if (chown_directory(path, orig_uid, orig_gid) != 0)
			{
				fprintf(stderr, "FAILED: chown %s to %d\n", path, orig_uid);
			}
		}
		if (dir == NULL || move_directory(path, dir) != 0)
		{
			fprintf(stderr, "FAILED: move %s %s\n", path, dir);
		}
		free(path);
	}
	if (dir != NULL)
	{
		free(dir);
	}
}

/**
 * Handles process signals.
 */
static void handle_signals(int sig)
{
	if (sig == SIGALRM)
	{
		fprintf(stderr, "Process exceeded time limit of %u seconds.\n", time_limit);
	}
	else
	{
		fprintf(stderr, "Process interrupted.\n");
	}
	if (pid != 0)
	{
		kill(pid, SIGKILL);
	}
	cleanup();
	_exit(1);
}

/**
 * Connects signals to handler.
 */
static void connect_signals()
{
	struct sigaction sa;
	sigemptyset(&sa.sa_mask);
	sa.sa_handler = handle_signals;
	sa.sa_flags = SA_RESTART;
	sigaction(SIGHUP, &sa, NULL);
	sigaction(SIGINT, &sa, NULL);
	sigaction(SIGQUIT, &sa, NULL);
	sigaction(SIGALRM, &sa, NULL);
	sigaction(SIGTERM, &sa, NULL);
}

int fail(const char *at)
{
	if (errno != 0)
	{
		fprintf(stderr, "[%s] errno=%d: %s\n", at, errno, strerror(errno));
	}
	return 1;
}

int limit_process(unsigned long int memory, unsigned long int files, unsigned long int disk)
{
	struct rlimit r;
	if (disk < ULONG_MAX)
	{
		r.rlim_cur = disk;
		r.rlim_max = disk;
		if (setrlimit(RLIMIT_FSIZE, &r) != 0)
		{
			fprintf(stderr, "FAILED: setrlimit RLIMIT_FSIZE=%lu\n", r.rlim_max);
			return fail("limit_process");
		}
	}
	if (files < ULONG_MAX)
	{
		r.rlim_cur = files;
		r.rlim_max = files;
		if (setrlimit(RLIMIT_NOFILE, &r) != 0)
		{
			fprintf(stderr, "FAILED: setrlimit RLIMIT_NOFILE=%lu\n", r.rlim_max);
			return fail("limit_process");
		}
	}
	if (memory < ULONG_MAX)
	{
		r.rlim_cur = memory;
		r.rlim_max = memory;
		if (setrlimit(RLIMIT_AS, &r) != 0)
		{
			fprintf(stderr, "FAILED: setrlimit RLIMIT_AS=%lu\n", r.rlim_max);
			return fail("limit_process");
		}
	}
	return 0;
}

unsigned long int parse_number(const char *argument)
{
	if (strcmp(argument, "-") == 0) return ULONG_MAX;
	char *end;
	unsigned long int res;
	res = strtoul(argument, &end, 10);
	if (end[0] == 'k' || end[0] == 'K')
	{
		res *= KB_IN_BYTES;
	}
	else if (end[0] == 'm' || end[0] == 'M')
	{
		res *= MB_IN_BYTES;
	}
	else if (end[0] == 'g' || end[0] == 'G')
	{
		res *= GB_IN_BYTES;
	}
	return res;
}

int chown_directory(const char *dir, uid_t uid, gid_t gid)
{
	// Change directory owner.
	if (lchown(dir, uid, gid) != 0) return fail("chown_directory");

	// Open directory.
	DIR *d;
	d = opendir(dir);
	if (!d) return fail("chown_directory");

	// Travel all directory entries.
	struct dirent *e;
	while ((e = readdir(d)) != NULL)
	{
		char path[strlen(dir) + strlen(e->d_name) + 2];
		strcpy(path, dir);
		strcat(path, "/");
		strcat(path, e->d_name);

		// Change file owner.
		if (e->d_type == DT_REG)
		{
			if (lchown(path, uid, gid) != 0) return fail("chown_directory");
		}

		// Process sub directories recursively.
		else if (e->d_type == DT_DIR)
		{
			if (strcmp(e->d_name, ".") != 0 && strcmp(e->d_name, "..") != 0)
			{
				if (chown_directory(path, uid, gid) != 0) return 1;
			}
		}
	}
	closedir(d);
	return 0;
}

int move_directory(const char *dir, const char *to)
{
	if (rename(dir, to) != 0)
	{
		if (errno == EXDEV)
		{
			if (copy_directory(dir, to) != 0) return 1;
		}
		else
		{
			return fail("move_directory");
		}
	}
	return 0;
}

int copy_directory(const char *dir, const char *to)
{
	struct stat keep_stat;
	if (stat(dir, &keep_stat) != 0) return fail("copy_directory");

	// Check or create target directory.
	struct stat path_stat;
	if (stat(to, &path_stat) != 0)
	{
		if(mkdir(to, keep_stat.st_mode) != 0) return fail("copy_directory");
	}
	if (lchown(to, keep_stat.st_uid, keep_stat.st_gid) != 0) return fail("copy_directory");

	// Open directory.
	DIR *d;
	d = opendir(dir);
	if (!d) return fail("copy_directory");

	// Travel all directory entries.
	struct dirent *e;
	while ((e = readdir(d)) != NULL)
	{
		char path[strlen(dir) + strlen(e->d_name) + 2];
		strcpy(path, dir);
		strcat(path, "/");
		strcat(path, e->d_name);
		char new_path[strlen(to) + strlen(e->d_name) + 2];
		strcpy(new_path, to);
		strcat(new_path, "/");
		strcat(new_path, e->d_name);

		// Copy file contents.
		if (e->d_type == DT_REG)
		{
			if (copy_file(path, new_path) != 0) return 1;
		}

		// Process sub directories recursively.
		else if (e->d_type == DT_DIR)
		{
			if (strcmp(e->d_name, ".") != 0 && strcmp(e->d_name, "..") != 0)
			{
				if (copy_directory(path, new_path) != 0) return 1;
			}
		}
	}
	closedir(d);
	if (rmdir(dir) != 0) return fail("copy_directory");
	return 0;
}

int copy_file(const char *file, const char *to)
{
	struct stat keep_stat;
	if (stat(file, &keep_stat) != 0) return fail("copy_file");

	int ff = open(file, O_RDONLY);
	if (ff < 0) return fail("copy_file");
	int ft = open(to, O_WRONLY | O_CREAT, keep_stat.st_mode);
	if (ft < 0) return fail("copy_file");
	ssize_t nread;
	char buf[4096];
	nread = read(ff, buf, sizeof buf);
	while (nread > 0)
	{
		char *ptr = buf;
		ssize_t nwrite;
		do {
			nwrite = write(ft, ptr, nread);
			if (nwrite >= 0)
			{
				nread -= nwrite;
				ptr += nwrite;
			}
			else if (errno != EINTR) return fail("copy_file");
		} while (nread > 0);
		nread = read(ff, buf, sizeof buf);
	}
	if (close(ft) != 0 || close(ff) != 0) return fail("copy_file");
	if (lchown(to, keep_stat.st_uid, keep_stat.st_gid) != 0) return fail("copy_file");
	if (unlink(file) != 0) return fail("copy_file");
	return 0;
}
