class ValidationFailed(Exception):
    def __init__(self, response):
        super(ValidationFailed, self).__init__("HTTP Reqeust validation failed")
        self.response = response
