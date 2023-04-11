from copy import copy


def calculate_grade(total_points, point_limits, pad_points):
    points = total_points['points']
    d_points = copy(total_points['points_by_difficulty'])

    def pass_limit(bound):
        if isinstance(bound, list): # pylint: disable=too-many-nested-blocks
            ds,ls = zip(*bound)
            for i,d in enumerate(ds):

                if pad_points:
                    p = d_points.get(d, 0)
                    l = ls[i] # noqa: E741
                    if p < l:
                        for j in range(i + 1, len(ds)):
                            jd = ds[j]
                            jp = d_points.get(jd, 0)
                            if jp > l - p:
                                d_points[jd] -= l - p
                                d_points[d] = l
                                break
                            p += jp
                            d_points[d] = p
                            d_points[jd] = 0
                    else:
                        continue

                if d_points.get(d, 0) < ls[i]:
                    return False

            return True
        return points >= bound

    grade = 0
    for bound in point_limits:
        if pass_limit(bound):
            grade += 1
        else:
            break
    return grade


def assign_grade(cached_points, diploma_design):

    if not (diploma_design and cached_points.user.is_authenticated):
        return -1

    if not diploma_design.course.is_course_staff(cached_points.user):
        avail = diploma_design.availability
        opt = diploma_design.USERGROUP
        external = cached_points.user.userprofile.is_external
        if (
            (avail == opt.EXTERNAL_USERS and not external)
            or (avail == opt.INTERNAL_USERS and external)
        ):
            return -1

    def is_passed(model):
        entry,_,_,_ = cached_points.find(model)
        return entry['passed']
    if not all(is_passed(m) for m in diploma_design.modules_to_pass.all()):
        return 0
    if not all(is_passed(e) for e in diploma_design.exercises_to_pass.all()):
        return 0

    return calculate_grade(
        cached_points.total(),
        diploma_design.point_limits,
        diploma_design.pad_points
    )
