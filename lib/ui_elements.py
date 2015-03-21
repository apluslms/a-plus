class Tab:
    def __init__(self, obj=None, label=None, url=None):
        if obj:
            self.url    = obj.get_absolute_url()
            self.label  = obj.get_label()
        else:
            self.url    = url
            self.label  = label
        
        self.active = False
    
    def get_absolute_url(self):
        return self.url
    
    def get_label(self):
        return self.label
