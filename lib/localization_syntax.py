

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
    if "|" in text:
        variants = text.split("|")
        exercise_number = variants[0] # Leading numbers or an empty string
        for variant in variants:
            if variant.startswith(lang + ":"):
                return exercise_number + variant[(len(lang)+1):]
        return exercise_number
    else:
        return text
