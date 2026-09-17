from collections import OrderedDict
from typing import List

from django.conf import settings

from exercise.cache.content import LearningObjectContent

# Generate students' results from this course instance
# Results are returned in a compact nested format with zeros omitted:
#
# JSON format example:
# {
#   "UserID": 13,
#   "exercises": {
#     "22": {"c": 3, "tb": 10, "tl": 8},
#     "48": {"c": 2, "tb": 2, "tl": 1, "uc": 1, "utb": 5, "utl": 3}
#   },
#   "totals": {"c": 12, "tb": 117, "tl": 100, "uc": 1, "utb": 5, "utl": 4}
# }
# Keys: c=official_count, tb=official_total_best, tl=official_total_last,
#       uc=unofficial_count, utb=unofficial_total_best, utl=unofficial_total_last

# pylint: disable-next=too-many-locals
def aggregate_points(profiles, taggings, exercises: List[LearningObjectContent], aggregate):
    DEFAULT_FIELDS = [
        'UserID', 'StudentID', 'Email', 'Name', 'Tags', 'Organization',
    ]

    agg = {}
    # Gather exercise points per student (now with official/all counts and best/last grades)
    for row in aggregate:
        ex = row['exercise_id']
        user_row = agg.get(row['submitters__user_id'], {})
        user_row[ex] = {
            'official_count': row['official_count'],
            'official_best': row['official_best'],
            'official_last': row['official_last'],
            'all_count': row['all_count'],
            'all_best': row['all_best'],
            'all_last': row['all_last'],
        }
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

        # Add exercise data in compact nested format with zeros omitted
        exercises_nested = {}
        if uid in agg:
            student_official_count = 0
            student_official_best = 0
            student_official_last = 0
            student_all_count = 0
            student_all_best = 0
            student_all_last = 0

            for ex_id, ex_data in agg[uid].items():
                student_official_count += ex_data['official_count']
                student_official_best += ex_data['official_best']
                student_official_last += ex_data['official_last']
                student_all_count += ex_data['all_count']
                student_all_best += ex_data['all_best']
                student_all_last += ex_data['all_last']

                # Compact nested format: include both best and last grades
                ex_nested = {
                    'c': ex_data['official_count'],
                    'tb': ex_data['official_best'],
                    'tl': ex_data['official_last']
                }

                # Only add unofficial fields if they differ from official (omit zeros)
                unofficial_count = ex_data['all_count'] - ex_data['official_count']
                unofficial_best = ex_data['all_best'] - ex_data['official_best']
                unofficial_last = ex_data['all_last'] - ex_data['official_last']
                if unofficial_count > 0:
                    ex_nested['uc'] = unofficial_count
                if unofficial_best > 0:
                    ex_nested['utb'] = unofficial_best
                if unofficial_last > 0:
                    ex_nested['utl'] = unofficial_last

                exercises_nested[str(ex_id)] = ex_nested

            # Add nested exercises object
            row['exercises'] = exercises_nested

            # Add totals in nested format with both best and last
            totals_nested = {
                'c': student_official_count,
                'tb': student_official_best,
                'tl': student_official_last
            }
            unofficial_total_count = student_all_count - student_official_count
            unofficial_total_best = student_all_best - student_official_best
            unofficial_total_last = student_all_last - student_official_last
            if unofficial_total_count > 0:
                totals_nested['uc'] = unofficial_total_count
            if unofficial_total_best > 0:
                totals_nested['utb'] = unofficial_total_best
            if unofficial_total_last > 0:
                totals_nested['utl'] = unofficial_total_last

            row['totals'] = totals_nested

        sheet.append(row)

    return sheet, DEFAULT_FIELDS
