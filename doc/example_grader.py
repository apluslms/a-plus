import SimpleHTTPServer, SocketServer, cgi
from urlparse import parse_qs

PORT = 8888

def grade_first_ex(submission):
  points = 0
  max_points = 2
  if "hello" in submission.lower():
    points += 1
  if "a+" in submission.lower():
    points += 1
  return (points,max_points)

class ExerciseGrader(SimpleHTTPServer.SimpleHTTPRequestHandler):

  # On GET-request return the exercise 
  def do_GET(self):
    response = open('first_exercise.html','r').read() 
    self.send_response(200)
    self.send_header('Content-type','text/html')    
    self.send_header("Content-Length", len(response))
    self.end_headers()
    self.wfile.write(response)

  # On POSTs get the answer, grade it and return the results
  def do_POST(self):
    length = int(self.headers.getheader('content-length'))
    postvars = parse_qs(self.rfile.read(length), keep_blank_values=1)
    points,max_points = grade_first_ex(postvars['answer'][0])

    response = '<html><head>\n' +\
                '<meta name="points" value="' + str(points) +'" />\n' +\
                '<meta name="max-points" value="' + str(max_points) + '" />\n' +\
                '<meta name="status" value="graded" />\n' + \
                '</head><body>' +\
                'Submission succesful,  you got ' + str(points) + '/' +\
                str(max_points)+ ' points!</body></html>'

    self.send_response(200)
    self.send_header('Content-type','text/html')    
    self.send_header("Content-Length", len(response))
    self.end_headers()
    self.wfile.write(response)

httpd = SocketServer.TCPServer(("", PORT), ExerciseGrader)
print "Serving at port:", PORT
httpd.serve_forever()
