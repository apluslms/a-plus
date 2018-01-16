'''
Utility functions for dictionaries.

'''
import docutils.core
import re


def iterate_kvp_with_dfs(node, key_regex=None):
    '''
    Iterate the key-value-parent tuples of a dictionary (or list) 'node'
    recursively with DFS.

    @type node: C{dict}
    @param node: the dictionary (or list) to iterate
    @type key_regex: C{re.RegexObject}
    @param key_regex: the key based item filter regex (optional)
    '''
    # Ensure the regex is compiled.
    if isinstance(key_regex, str):
        key_regex = re.compile(key_regex)
    if not key_regex:
        return

    # Iterate node structure recursively.
    if isinstance(node, dict):
        iterator = node.items()
    elif isinstance(node, list):
        iterator = enumerate(node)
    else:
        raise TypeError
    for child_key, child_value in iterator:
        if isinstance(child_value, dict) or isinstance(child_value, list):
            for sub_key, sub_value, sub_node in iterate_kvp_with_dfs(child_value, key_regex):
                yield sub_key, sub_value, sub_node

        # Yield matching key-value-parent tuples.
        if key_regex.match(str(child_key)):
            yield child_key, child_value, node


def get_rst_as_html(rst_str):
    '''
    Return a string with RST formatting as HTML.

    @type rst_str: C{str}
    @param rst_str: the RST string to convert
    @rtype : C{str}
    @return: the resulting HTML string
    '''
    parts = docutils.core.publish_parts(source=rst_str, writer_name='html')
    return parts['fragment']
