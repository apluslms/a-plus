class ModuleTree(object):
    """
    Holds static learning object tree to generate table of contents and
    different navigation elements as required.
    """

    def __init__(self, module):
        self.module = module
        self.objects = list(module.learning_objects.all())
        for o in self.objects:
            o.course_module = module

    def children(self, parent_id=None, show_hidden=False):
        if show_hidden:
            return [o for o in self.objects if o.parent_id == parent_id]
        return [o for o in self.objects if o.parent_id == parent_id \
            and o.status in ('ready', 'maintenance')]

    def parent(self, ref):
        if ref.parent_id:
            for o in self.objects:
                if o.id == ref.parent_id:
                    return o
        return None

    def next(self, ref):
        children = self.children(ref.id)
        n = children[0] if children else self.next_sibling(ref)
        return self.next(n) if n and n.is_empty() \
            else n or self.module.next_module()

    def next_sibling(self, ref):
        siblings = [o for o in self.children(ref.parent_id) \
            if o.order > ref.order]
        return siblings[0] if siblings else \
            (self.next_sibling(self.parent(ref)) if ref.parent_id else None)

    def first(self):
        children = self.children(None)
        if children:
            n = children[0]
            return self.next(n) if n and n.is_empty() else n
        return None

    def last_child(self, ref=None):
        children = self.children(ref.id if ref else None)
        if children:
            return self.last_child(children[-1])
        return ref

    def previous(self, ref):
        siblings = [o for o in self.children(ref.parent_id) \
            if o.order < ref.order]
        n = self.last_child(siblings[-1]) if siblings else self.parent(ref)
        n = self.previous(n) if n and n.is_empty() else n
        return n or self.module

    def last(self):
        n = self.last_child()
        return self.previous(n) if n and n.is_empty() else n or self.module

    def flat(self, parent=None, with_sub_markers=True, show_hidden=False):
        def recursion(parent_id):
            container = []
            children = self.children(parent_id, show_hidden)
            if children:
                if with_sub_markers:
                    container.append({'sub':'open'})
                for current in children:
                    container.append(current)
                    container.extend(recursion(current.id))
                if with_sub_markers:
                    container.append({'sub':'close'})
            return container
        return recursion(parent.parent_id if parent else None)

    def parents(self, ref):
        n = self.parent(ref)
        parents = self.parents(n) if n else []
        parents.append(ref)
        return parents

    def by_path(self, path):
        for hit in [o for o in self.objects if o.url == path[-1]]:
            if self.check_path(hit, path):
                return hit
        return None

    def check_path(self, ref, path):
        if ref and path:
            if ref.url != path[-1]:
                return False
            return self.check_path(self.parent(ref), path[:-1])
        return not (ref or path)

    def renumber(self, start=1):
        def recursion(parent_id, start=1):
            n = start
            for o in self.children(parent_id):
                o.order = n
                o.save()
                recursion(o.id)
                n += 1
            return n
        return recursion(None, start=start)
