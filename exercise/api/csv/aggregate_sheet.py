from collections import OrderedDict

from ...cache.points import CachedPoints


def aggregate_sheet(request, instance, content, profiles):
    DEFAULT_FIELDS = [
      'UserID', 'StudentID', 'Email', 'Total', 'Max',
    ]
    DIFFICULTY_FIELD = "Total {}"
    OBJECT_FIELDS = [
      ("{} Count", 'submission_count'),
      ("{} Total", 'points'),
      ("{} Max", 'max_points'),
    ]
    sheet = []
    fields = DEFAULT_FIELDS.copy()

    difficulties = []
    for key in content.total()['max_points_by_difficulty']:
      if key:
        difficulties.append(key)
        fields.append(DIFFICULTY_FIELD.format(key))
    for entry in content.flat_full():
      if entry['type'] != 'level':
        for name,key in OBJECT_FIELDS:
          fields.append(name.format(entry['number']))

    for profile in profiles:
        points = CachedPoints(instance, profile.user, content)
        total = points.total()
        row = OrderedDict([
            ('UserID', profile.user.id),
            ('StudentID', profile.student_id),
            ('Email', profile.user.email),
            ('Total', total['points']),
            ('Max', total['max_points']),
        ])
        for key in difficulties:
            row[DIFFICULTY_FIELD.format(key)] = total['points_by_difficulty'].get(key, 0)
        for entry in points.flat_full():
            if entry['type'] != 'level':
                for name,key in OBJECT_FIELDS:
                    row[name.format(entry['number'])] = entry[key]
        sheet.append(row)

    return sheet,fields
