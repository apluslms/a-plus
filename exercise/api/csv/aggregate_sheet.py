from collections import OrderedDict
import json

from ...cache.points import CachedPoints


def aggregate_sheet(request, profiles, taggings, exercises, aggregate, number):
    DEFAULT_FIELDS = [
      'UserID', 'StudentID', 'Email', 'Tags',
    ]
    OBJECT_FIELDS = [
      '{} Count', '{} Total', '{} Ratio',
    ]

    d = 1 + (len(number.split('.')) if number else 0)
    exercise_map = {}
    exercise_max = {}
    exercise_fields = []
    exercise_nums = []
    num = None
    for e in exercises:
        if len(e['number'].split('.')) == d:
            num = e['number']
            exercise_nums.append(num)
            exercise_max[num] = 0
            for n in OBJECT_FIELDS:
                exercise_fields.append(n.format(e['number']))
            if e['type'] == 'exercise':
                exercise_map[e['id']] = num
                exercise_max[num] += e['max_points']
        elif e['type'] == 'exercise':
            exercise_map[e['id']] = num
            exercise_max[num] += e['max_points']

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

    tags = {}
    for t in taggings:
        if t.user_id in tags:
            tags[t.user_id].append(str(t.tag_id))
        else:
            tags[t.user_id] = [str(t.tag_id)]

    sheet = []
    for profile in profiles:
        uid = profile.user.id
        user_row = agg.get(uid, {})
        user_tags = ['mooc' if profile.is_external else 'aalto']
        user_tags.extend(tags.get(uid, []))
        row = OrderedDict([
            ('UserID', uid),
            ('StudentID', profile.student_id),
            ('Email', profile.user.email),
            ('Tags', '|'.join(user_tags)),
        ])
        for i,num in enumerate(exercise_nums):
            values = user_row.get(num, [0,0])
            maxp = exercise_max[num]
            for j in [0,1]:
                row[exercise_fields[3 * i + j]] = values[j]
            row[exercise_fields[3 * i + 2]] = (
                values[1] / maxp if maxp > 0 else
                1 if values[0] > 0 else 0
            )
        sheet.append(row)

    return sheet, DEFAULT_FIELDS + exercise_fields
