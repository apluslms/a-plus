

def format_localization(element):
    """
    Parse localised elements into |lang:val|lang:val| -format strings
    """
    if isinstance(element, dict):
        strings = ("{}:{}".format(k, v) for k, v in element.items())
        return "|{}|".format("|".join(strings))
    return str(element)


def pick_localized(entry, lang):
    """
    Picks the selected language's value from
    |lang:value|lang:value| -format text.
    """
    text = entry if isinstance(entry, str) else str(entry)
    variants = text.split('|')
    if len(variants) > 2:
        prefix = variants[0]
        suffix = variants[-1]
        variants = variants[1:-1]
        for variant in variants:
            if variant.startswith(lang + ":"):
                return prefix + variant[(len(lang)+1):] + suffix
        for variant in variants:
            if ':' in variant:
                return prefix + variant.split(':', 1)[1] + suffix
    return text


def parse_localized(entry):
    """
    Returns a list of pairs of language and value from
    |lang:value|lang:value| -format text.
    If there is no language, then the first item in the tuple will be None.
    """
    text = entry if isinstance(entry, str) else str(entry)
    variants = text.split('|')
    if len(variants) < 2:
        return [(None, text)]

    prefix = variants[0]
    suffix = variants[-1]
    entries = []
    for variant in variants[1:-1]:
        if not variant:
            continue
        lang, colon, data = variant.partition(':')
        if not colon or data.startswith('//') or len(lang.split('-')[0]) > 3:
            lang, data = None, variant
        entries.append((lang, ''.join((prefix, data, suffix))))
    return entries
