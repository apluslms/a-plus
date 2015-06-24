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
    if b'hello' in submission.lower():
        points += 1
    if b'a+' in submission.lower():
        points += 1
    return (points,max_points)

class ExerciseGrader(http.server.BaseHTTPRequestHandler):

    # On GET-request return the exercise
    def do_GET(self):

        # Simple exercise
        if '/first_exercise/' in self.path:
            response = open('first_exercise.html','r').read()
            self._respond(response.encode('utf-8'))

        # Attachment exercise
        elif '/attachment_exercise/' in self.path:
            response = open('attachment_exercise.html','r').read()
            self._respond(response.encode('utf-8'))
        
        # Ajax exercise
        elif '/ajax_exercise/' in self.path:
            response = open('ajax_exercise.html','r').read()
            url = 'http://localhost:' + str(PORT) + self.path
            response = response.replace('{{url}}', url)
            self._respond(response.encode('utf-8'))

    # On POSTs get the answer, grade it and return the results
    def do_POST(self):
        length = int(self.headers.get('content-length'))
        ctype, _ = cgi.parse_header(self.headers.get('content-type'))
        if ctype == 'multipart/form-data':
            post_data = self.rfile.read(length)
        elif ctype == 'application/x-www-form-urlencoded':
            post_data = cgi.parse_qs(self.rfile.read(length), keep_blank_values=1)
        else:
            post_data = {}

        # Simple exercise
        if '/first_exercise/' in self.path:
            points, max_points = grade_first_ex(post_data[b'answer'][0])
            response = '<html><head>\n' +\
                       '<meta name="points" value="' + str(points) +'" />\n' +\
                       '<meta name="max-points" value="' + str(max_points) + '" />\n' +\
                       '<meta name="status" value="graded" />\n' + \
                       '</head><body>' +\
                       'Submission succesful,  you got ' + str(points) + '/' +\
                       str(max_points)+ ' points!</body></html>'
            self._respond(response.encode('utf-8'))

        # Attachment exercise. Note that the file is only stored in A+
        elif '/attachment_exercise/' in self.path:
            response = '<html><head>\n' +\
                       '<meta name="points" value="0" />\n' +\
                       '<meta name="max-points" value="100" />\n' +\
                       '<meta name="status" value="waiting" />\n' + \
                       '</head><body>Submission stored, ' +\
                       'you will be notified when it is assessed.</body></html>'
            self._respond(response.encode('utf-8'))

        # AJAX exercise
        # NOTE: The AJAX request comes from the user's browser, not A+
        #       We will now send the score to A+ using the submission URL
        elif '/ajax_exercise/' in self.path:
            points = post_data[b'points'][0]
            max_points = post_data[b'max_points'][0]

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
            response = opener.open(submission_url, request_data, timeout=10).read()
            
            self._respond(response, headers={ 'Access-Control-Allow-Origin': '*' })

        # Attached exercise rule file in the POST
        elif '/attached_exercise/' in self.path:
            ok = 'Content-Disposition: form-data; name="content_0";' in str(post_data)
            msg = 'Seems like a proper' if ok else 'Unexpected'
            response = '<html><head>\n' +\
                       '<meta name="points" value="' + str(100 if ok else 0) + '" />\n' +\
                       '<meta name="max-points" value="100" />\n' +\
                       '<meta name="status" value="graded" />\n' + \
                       '</head><body>' + msg + ' POST was created.</body></html>'
            self._respond(response.encode('utf-8'))

        # Demonstrating hook functionality
        elif "/hook/" in self.path:
            response = '<html><body><p>POST Hook detected!</p><ul>\n'
            response += '<li id="path">Path: <pre>{}</pre></li>\n'.format(self.path)
            for key, value in post_data.items():
                response += '<li id="{}">{}: <pre>{}</pre></li>\n'.format(key, key, value)
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

httpd = http.server.HTTPServer(('', PORT), ExerciseGrader)
print('Serving at port:', PORT)
try:
    httpd.serve_forever()
except Exception as e:
    httpd.server_close()
    raise e
