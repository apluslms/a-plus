

def format_localization(element):
    """
    Parse localised elements into |lang:val|lang:val| -format strings
    """
    if isinstance(element, dict):
        strings = ("{}:{}".format(k, v) for k, v in element.items())
        return "|{}|".format("|".join(strings))
    else:
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
