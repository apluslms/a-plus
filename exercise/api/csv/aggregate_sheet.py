from collections import OrderedDict


def aggregate_sheet(profiles, taggings, exercises, aggregate, number): # pylint: disable=too-many-locals
    DEFAULT_FIELDS = [
      'UserID', 'StudentID', 'Email', 'Tags',
    ]
    OBJECT_FIELDS = [
      '{} Count', '{} Total', '{} Ratio',
    ]
    # Count: number of submissions.
    # Total: (best) points.
    # Ratio: float between 0-1, the percentage of points / max_points.

    d = 1 + (len(number.split('.')) if number else 0)
    # If the number parameter is not given, all modules in the course are included.
    # If the number is given, the children below that level are included.
    # Example: number = "1" (module 1), d = 2, the output includes chapters in the fields: 1.1, 1.2, 1.3, ...
    # (The exercises are aggregated under their parent chapters.)
    exercise_map = {}
    exercise_max = {}
    exercise_fields = []
    exercise_nums = []
    num = None
    for e in exercises:
        level = len(e['number'].split('.'))
        enum = '.'.join(e['number'].split('.')[:d])
        # num needs to be checked here because in some cases, the exercises list
        # is missing parents for some exercises. Especially when search
        # entries are filtered with the filter_for_assistant parameter.
        if level == d or (level > d and num != enum):
            # Object in the level to include. If this object has children,
            # the variables are initialized here. The children come after
            # the parent in the exercises list.
            # The children enter the next if branch since their level is higher.
            num = e['number'] if level == d else enum
            exercise_nums.append(num)
            exercise_max[num] = 0
            for n in OBJECT_FIELDS:
                exercise_fields.append(n.format(num))
            if e['type'] == 'exercise':
                exercise_map[e['id']] = num
                exercise_max[num] += e['max_points']
        elif level > d:
            # Child object of the previous parent.
            # Parent comes before its children in the exercises list.
            exercise_map[e['id']] = num
            exercise_max[num] += e['max_points']

    agg = {}
    for row in aggregate:
        uid = row['submitters__user_id']
        num = exercise_map.get(row['exercise_id'], None)
        if num is None:
            continue
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
