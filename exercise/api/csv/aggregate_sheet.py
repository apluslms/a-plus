from collections import OrderedDict

from ...cache.points import CachedPoints


def aggregate_sheet(request, profiles, exercises, aggregate, number):
    DEFAULT_FIELDS = [
      'UserID', 'StudentID', 'Email',
    ]
    OBJECT_FIELDS = [
      '{} Count', '{} Total',
    ]

    d = 1 + (len(number.split('.')) if number else 0)
    exercise_map = {}
    exercise_nums = []
    exercise_fields = []
    num = None
    for e in exercises:
        if len(e['number'].split('.')) == d:
            num = e['number']
            exercise_nums.append(num)
            for n in OBJECT_FIELDS:
                exercise_fields.append(n.format(e['number']))
            if e['type'] == 'exercise':
                exercise_map[e['id']] = num
        elif e['type'] == 'exercise':
            exercise_map[e['id']] = num

    agg = {}
    for row in aggregate:
        uid = row['submitters__user_id']
        num = exercise_map[row['exercise_id']]
        user_row = agg.get(uid, {})
        values = user_row.get(num, [0,0])
        values[0] += row['count']
        values[1] += row['total']
        user_row[num] = values
        agg[uid] = user_row

    sheet = []
    for profile in profiles:
        uid = profile.user.id
        user_row = agg.get(uid, {})
        row = OrderedDict([
            ('UserID', uid),
            ('StudentID', profile.student_id),
            ('Email', profile.user.email),
        ])
        for i,num in enumerate(exercise_nums):
            values = user_row.get(num, [0,0])
            for j in [0,1]:
                row[exercise_fields[2 * i + j]] = values[j]
        sheet.append(row)

    return sheet, DEFAULT_FIELDS + exercise_fields
