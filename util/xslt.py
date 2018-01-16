'''
Utilities for handling XSLT tranform.

'''
from lxml import etree


def transform(source, xsl_file_name):
    '''
    Transforms XML source using XSL rules.

    @type source_file: C{str}
    @param source_file: XML contents to transform
    @type xsl_file_name: C{str}
    @param xsl_file_name: an XSL rule file
    @rtype: C{str}
    @return: transformed content
    '''
    dom = etree.fromstring(source.encode('utf-8'))
    xslt = etree.parse(xsl_file_name)
    transform = etree.XSLT(xslt)
    newdom = transform(dom)
    return str(newdom)
