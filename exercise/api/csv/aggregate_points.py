from django.conf import settings
from collections import OrderedDict

# Generate students' results from this course instance
# Only exercises in which student has submitted answers will be returned
# to save bandwidth. Exercise points are returned in the form:
# xx Count: yy, xx Total: zz
# where xx is the exercise id, yy the submission count and zz the exercise points.
# For convenience, we also return the total submission count and points for student

def aggregate_points(profiles, taggings, exercises, aggregate): # pylint: disable=too-many-locals
    DEFAULT_FIELDS = [
        'UserID', 'StudentID', 'Email', 'Name', 'Tags', 'Organization', 'Count', 'Total',
    ]
    OBJECT_FIELDS = [
        '{} Count', '{} Total',
    ]

    exercise_fields = []

    for e in exercises:
        if e['type'] == 'exercise':
            for n in OBJECT_FIELDS:
                exercise_fields.append(n.format(e['id']))

    agg = {}
    # Gather exercise points per student
    for row in aggregate:
        ex = row['exercise_id']

        values = [row['count'],row['total']]
        user_row = agg.get(row['submitters__user_id'], {})
        user_row[ex] = values
        agg[row['submitters__user_id']] = user_row

    # Prefetch all tag_id - user_id pairs at once from DB to avoid multiple queries
    # TODO: Ideally this should probably be done in api.csv.views
    all_tags = list(taggings.all().values('user_id','tag_id'))

    sheet = []

    for profile in profiles:
        uid = profile.user.id
        user_row = agg.get(uid, {})
        user_tags = [
            settings.EXTERNAL_USER_LABEL.lower() if profile.is_external else settings.INTERNAL_USER_LABEL.lower()
        ]
        # Instead of filtering the Django resultset (which causes a new DB query),
        # we find the users' tags manually from the prefetched array of dicts
        other_tags = list(item for item in all_tags if item["user_id"] == profile.id)
        #other_tags = all_tags.all().filter(user_id=profile.id)
        for tag in other_tags:
            user_tags.append(str(tag['tag_id']))
        #user_tags.extend(tags.get(uid, []))
        row = OrderedDict([
            ('UserID', uid),
            ('Email', profile.user.email),
            ('StudentID', profile.student_id),
            ('Name', profile.user.first_name + ' ' + profile.user.last_name),
            ('Tags', '|'.join(user_tags)),
            ('Organization', profile.organization),
        ])

        # Add submitted exercise count and points of the user as labeled dictionary items
        # so for example if agg[uid] is {14: [1,10]}, it is turned into:
        # "14 Count": 1
        # "14 Total": 10
        #
        if uid in agg:
            student_totalsubs = 0
            student_totalscore = 0
            try:
                for e in agg[uid]:
                    row[str(e) + ' Count'] = agg[uid][e][0]
                    student_totalsubs += agg[uid][e][0]
                    row[str(e) + ' Total'] = agg[uid][e][1]
                    student_totalscore += agg[uid][e][1]
            except KeyError:
                pass

            # Add totals per student
            row['Count'] = student_totalsubs
            row['Total'] = student_totalscore

        sheet.append(row)

    return sheet, DEFAULT_FIELDS + exercise_fields
