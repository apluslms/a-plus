import http.server, socketserver
from urllib.parse import parse_qs
import urllib.request, urllib.parse, urllib.error

PORT = 8888

def grade_first_ex(submission):
    points = 0
    max_points = 2
    if b'hello' in submission.lower():
        points += 1
    if b'a+' in submission.lower():
        points += 1
    return (points,max_points)

class ExerciseGrader(http.server.SimpleHTTPRequestHandler):

    # On GET-request return the exercise
    def do_GET(self):

        # Simple exercise
        if '/first_exercise/' in self.path:
            response = open('first_exercise.html','r').read().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)
        # Attachment exercise
        elif '/attachment_exercise/' in self.path:
            response = open('attachment_exercise.html','r').read().encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)
        elif '/ajax_exercise/' in self.path:
            response = open('ajax_exercise.html','r').read()
            url = 'http://localhost:' + str(PORT) + self.path
            response = response.replace('{{url}}', url).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)

    # On POSTs get the answer, grade it and return the results
    def do_POST(self):
        length = int(self.headers.get('content-length'))
        post_data = parse_qs(self.rfile.read(length), keep_blank_values=1)

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
            response = response.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)

        # Attachment exercise. Note that the file is only stored in A+
        elif '/attachment_exercise/' in self.path:
            response = '<html><head>\n' +\
                       '<meta name="points" value="0" />\n' +\
                       '<meta name="max-points" value="100" />\n' +\
                       '<meta name="status" value="waiting" />\n' + \
                       '</head><body>Submission stored, ' +\
                       'you will be notified when it is assessed.</body></html>'
            response = response.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)

        # AJAX exercise
        # NOTE: The AJAX request comes from the user's browser, not A+
        #       We will now send the score to A+ using the submission URL
        elif '/ajax_exercise/' in self.path:
            points = post_data[b'points'][0]
            max_points = post_data[b'max_points'][0]
            submission_url = parse_qs(self.path.split('?')[1])['submission_url'][0]
            request_dict = {
                'points': points,
                'max_points': max_points,
                'feedback': 'You got %s / %s points for your answer.' % (points, max_points),
                'grading_payload': '{}'
            }
            # Submit the score to A+
            opener = urllib.request.build_opener()
            request_data = urllib.parse.urlencode(request_dict).encode('utf-8')
            response = opener.open(submission_url, request_data, timeout=10).read()
            # Create the response
            self.send_response(200)
            self.send_header('Content-type','text/html')
            self.send_header('Content-Length', len(response))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)

        # Demonstrating hook functionality
        elif "/hook/" in self.path:
            print("POST Hook detected!", self.path)
            print("Data:", post_data)
            self.send_response(200)
            self.send_header('Content-type','example')
            self.send_header('Content-Length', 0)
            self.end_headers()
            self.wfile.write(b'')

httpd = socketserver.TCPServer(('', PORT), ExerciseGrader)
print('Serving at port:', PORT)
httpd.serve_forever()
