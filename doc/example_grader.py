import sys, cgi, http.server
import urllib.request, urllib.parse

PORT = 8888

if len(sys.argv) > 2:
    print('Usage: %s [port-number]' % (sys.argv[0]))
    exit(0)
if len(sys.argv) == 2:
    PORT = int(sys.argv[1])

def grade_first_ex(submission):
    points = 0
    max_points = 2
    if 'hello' in submission.lower():
        points += 1
    if 'a+' in submission.lower():
        points += 1
    return (points,max_points)

class ExerciseGrader(http.server.BaseHTTPRequestHandler):

    # On GET-request return the exercise.
    def do_GET(self):

        # Simple exercise expecting a field value.
        if '/first_exercise/' in self.path:
            response = open('first_exercise.html','r').read()
            self._respond(response.encode('utf-8'))

        # An exercise that expects a file submission.
        elif '/file_exercise/' in self.path:
            response = open('file_exercise.html','r').read()
            self._respond(response.encode('utf-8'))

        # An exercise that uses AJAX to create submissions.
        elif '/ajax_exercise/' in self.path:
            response = open('ajax_exercise.html','r').read()
            url = 'http://localhost:' + str(PORT) + self.path
            response = response.replace('{{url}}', url)
            self._respond(response.encode('utf-8'))

    # On POSTs get the answer, grade it and return the results.
    def do_POST(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': self.headers['Content-Type'],
            })

        # Simple exercise expecting a field value.
        if '/first_exercise/' in self.path:
            points, max_points = grade_first_ex(form.getfirst('answer', ''))
            response = '<html><head>\n' +\
                       '<meta name="points" value="' + str(points) +'" />\n' +\
                       '<meta name="max-points" value="' + str(max_points) + '" />\n' +\
                       '<meta name="status" value="graded" />\n' + \
                       '</head><body>' +\
                       '<div class="alert alert-success">' +\
                       'Submission succesful,  you got ' + str(points) + '/' +\
                       str(max_points)+ ' points!</div></body></html>'
            self._respond(response.encode('utf-8'))

        # An exercise that expects a file submission.
        # Note that the file is only stored in A+ for manual assessment.
        elif '/file_exercise/' in self.path:
            if not 'myfile' in form or not form['myfile'].filename:
                status = 'error'
                msg = 'Error: missing the submission file.'
            else:
                status = 'accepted'
                msg = '<div class="alert alert-success">' +\
                      'Submission stored, you will be notified when course ' +\
                      'staff has assessed it.</div>'
            response = '<html><head>\n' +\
                       '<meta name="status" value="' + status + '" />\n' + \
                       '</head><body>' + msg + '</body></html>'
            self._respond(response.encode('utf-8'))

        # An exercise that uses AJAX to create submissions.
        # NOTE: The AJAX request comes from the user's browser, not A+
        #       We will now send the score to A+ using the submission URL.
        elif '/ajax_exercise/' in self.path:
            points = form.getfirst('points', 0)
            max_points = form.getfirst('max_points', 0)

            # Submit the score to A+
            submission_url = urllib.parse.parse_qs(self.path.split('?')[1])['submission_url'][0]
            request_dict = {
                'points': points,
                'max_points': max_points,
                'feedback': 'You got %s / %s points for your answer.' % (points, max_points),
                'grading_payload': '{}'
            }
            opener = urllib.request.build_opener()
            request_data = urllib.parse.urlencode(request_dict).encode('utf-8')
            try:
                response = opener.open(submission_url, request_data, timeout=10).read()
                status_code = 200
            except urllib.error.HTTPError as e:
                response = e.read()
                status_code = 500
            self._respond(response, status_code=status_code, headers={ 'Access-Control-Allow-Origin': '*' })

        # Exercise with attachment expects course staff selected files.
        elif '/attached_exercise/' in self.path:
            if not 'content_0' in form or not form['content_0'].filename \
            or not 'content_1' in form or not form['content_1'].filename \
            or form.getfirst('file_1', '') != 'test.txt':
                status = 'error'
                msg = 'Error: unexpected files in the POST.'
                points, max_points = (0, 2)
            else:
                status = 'graded'
                data1 = form['content_0'].file.read().decode('utf-8')
                data2 = form['content_1'].file.read().decode('utf-8')
                if data2 in data1:
                    points = 1
                    msg = 'The submitted file contents were included in the exercise attachment.'
                else:
                    points = 0
                    msg = 'The submitted file contents were not included in the exercise attachment.'
            response = '<html><head>\n' +\
                       '<meta name="points" value="' + str(points) + '" />\n' +\
                       '<meta name="max-points" value="1" />\n' +\
                       '<meta name="status" value="' + status + '" />\n' + \
                       '</head><body>' + msg + '</body></html>'
            self._respond(response.encode('utf-8'))

        # Demonstrating hook functionality
        elif "/hook/" in self.path:
            response = '<html><body><p>POST Hook detected!</p><ul>\n'
            response += '<li id="path">Path: <pre>{}</pre></li>\n'.format(self.path)
            for key in form.keys():
                response += '<li id="{}">{}: <pre>{}</pre></li>\n'.format(key, key, form[key].value)
            response += '</ul></body></html>'
            self._respond(response.encode('utf-8'))

    def _respond(self, content, content_type='text/html', status_code=200, headers={}):
        hdrs = {
            'Content-Type': content_type,
            'Content-Length': len(content),
        }
        hdrs.update(headers)
        self.send_response(status_code)
        for key, value in hdrs.items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(content)

httpd = http.server.HTTPServer(('127.0.0.1', PORT), ExerciseGrader)
print('Serving at port:', PORT)
try:
    httpd.serve_forever()
except Exception as e:
    httpd.server_close()
    raise e
