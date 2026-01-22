function participants_list(participants, api_url, is_teacher, enrollment_statuses) {
  // Ensure predictable order by student id
  participants.sort(function(a, b) { return a.id.localeCompare(b.id); });

  // Minimal HTML escape helper
  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Normalize/ensure tag_slugs are present using tag_ids and page tag metadata when available
  // We'll also compute these again on demand when filtering/drawing, but precomputing helps initial render
  function ensureTagSlugs(p) {
    if (Array.isArray(p.tag_slugs) && p.tag_slugs.length) {
      // Unique-ify
      const set = new Set(p.tag_slugs);
      p.tag_slugs = Array.from(set);
      return p.tag_slugs;
    }
    const byId = getTagMapById();
    const derived = Array.isArray(p.tag_ids) ? p.tag_ids.map(function(id){ return byId[id] ? byId[id].slug : null; }).filter(Boolean) : [];
    const set = new Set(derived);
    p.tag_slugs = Array.from(set);
    return p.tag_slugs;
  }

  // Tooltips for filter buttons using data-description
  function initFilterButtonDescriptions() {
    if (typeof bootstrap === 'undefined' || !bootstrap.Tooltip) return;
    $('.filter-users button.filter-tag').each(function(){
      const $btn = $(this);
      const desc = $btn.attr('data-description');
      try { const pop = bootstrap.Popover && bootstrap.Popover.getInstance(this); if (pop) pop.dispose(); } catch (e) {}
      try { const tip = bootstrap.Tooltip && bootstrap.Tooltip.getInstance(this); if (tip) tip.dispose(); } catch (e) {}
      $btn.removeAttr('data-bs-title data-bs-content data-bs-toggle');
      if (!desc || !desc.trim()) return;
      $btn.attr('title', desc);
      try { new bootstrap.Tooltip(this, { title: desc, trigger: 'hover focus', placement: 'top', container: 'body' }); } catch (e) {}
    });
  }

  // Read all tags from filter buttons (serves as page-local tag metadata)
  function getAllPageTags() {
    return $('.filter-users button.filter-tag').map(function(){
      const $b = $(this);
      let id = parseInt($b.attr('data-tagid'), 10);
      if (isNaN(id)) id = null; // hardcoded tags have no numeric id
      return {
        id: id,
        slug: $b.attr('data-tagslug'),
        name: $b.attr('data-tagname') || $b.text().trim(),
        color: $b.attr('data-color'),
        font_color: $b.attr('data-font-color'),
        font_white: $b.attr('data-font-white') === '1'
      };
    }).get();
  }

  // Cached tag metadata maps
  let _tagMapById = null;
  let _tagMapBySlug = null;
  function getTagMapById() {
    if (_tagMapById) return _tagMapById;
    _tagMapById = {};
    _tagMapBySlug = {};
    getAllPageTags().forEach(function(t){
      if (t.id !== null && t.id !== undefined) _tagMapById[t.id] = t;
      if (t.slug) _tagMapBySlug[t.slug] = t;
    });
    return _tagMapById;
  }
  function getTagMapBySlug() {
    if (_tagMapBySlug) return _tagMapBySlug;
    getTagMapById();
    return _tagMapBySlug;
  }
  function upsertTagMeta(tag) {
    if (!_tagMapById || !_tagMapBySlug) getTagMapById();
    if (tag && (tag.slug || tag.id != null)) {
      if (tag.id != null) _tagMapById[tag.id] = tag;
      if (tag.slug) _tagMapBySlug[tag.slug] = tag;
    }
  }

  // Render a single tag label from slug using page metadata; fallback to slug text
  function renderTagLabel(slug) {
    const meta = getTagMapBySlug()[slug];
    const label = meta ? meta.name : slug;
    const tagIdAttr = meta && meta.id != null ? ' data-tagid="' + String(meta.id) + '"' : '';
    // Inline styles to ensure colors apply even without CSS variables
    let styles = [];
    if (meta && meta.color) styles.push('background-color:' + meta.color);
    if (meta && (meta.font_color || meta.font_white)) {
      const fontColor = meta.font_color ? meta.font_color : (meta.font_white ? '#fff' : '');
      if (fontColor) styles.push('color:' + fontColor);
    }
    const styleAttr = styles.length ? ' style="' + styles.join(';') + '"' : '';
    return '<span class="colortag badge badge-xs" data-tagslug="' + slug + '"' + tagIdAttr + styleAttr + '>' + escapeHtml(label) + '</span>';
  }

  // Render the tags cell for a row (use tag_slugs only)
  function renderTagsCell(row) {
    const slugs = ensureTagSlugs(row);
    if (!slugs || !slugs.length) return '';
    return slugs.map(renderTagLabel).join(' ');
  }

  // Open Add Tag modal for provided user IDs
  function openAddTagModal(userIds, preselectSlug) {
    const allTags = getAllPageTags().filter(function(t){
      return t.id !== null && t.id !== undefined;
    });
    const selectedParticipants = participants.filter(function(p){ return userIds.indexOf(p.user_id) !== -1; });
    let commonSlugs = null;
    selectedParticipants.forEach(function(p){
      const set = new Set(ensureTagSlugs(p));
      if (commonSlugs === null) {
        commonSlugs = new Set(set);
      } else {
        commonSlugs.forEach(function(s){ if (!set.has(s)) commonSlugs.delete(s); });
      }
    });
    const $select = $('#tag-add-select');
    $select.empty();
    allTags.forEach(function(tag){
      const disabled = commonSlugs && commonSlugs.has(tag.slug);
      const $opt = $('<option/>')
        .attr({ value: tag.slug, 'data-tagid': tag.id, 'data-color': tag.color, 'data-font_color': tag.font_color, 'data-font_white': tag.font_white ? '1':'0' })
        .prop('disabled', !!disabled)
        .text(tag.name);
      $select.append($opt);
    });
    if (preselectSlug) {
      $select.val(preselectSlug);
    } else {
      const $firstEnabled = $select.find('option:not([disabled])').first();
      if ($firstEnabled.length) $select.val($firstEnabled.val());
    }
    const hasAvailable = $select.find('option:not([disabled])').length > 0;
    $('#tag-add-confirm').prop('disabled', !hasAvailable);
    $('#tag-add-target-count').text(userIds.length);
    $('#tag-add-confirm').data('targetUserIds', userIds);
    const modal = new bootstrap.Modal('#tag-add-modal', {});
    modal.show();
  }

  function collectTagSlugsForUsers(userIds) {
    const set = new Set();
    participants.forEach(function(p){
      if (userIds.indexOf(p.user_id) !== -1) {
        ensureTagSlugs(p).forEach(function(s){ set.add(s); });
      }
    });
    return Array.from(set).filter(function(slug){
      return slug !== 'user-external' && slug !== 'user-internal';
    });
  }

  function openRemoveTagModal(userIds) {
    const slugs = collectTagSlugsForUsers(userIds);
    const $select = $('#tag-remove-select');
    $select.empty();
    const slugMap = getTagMapBySlug();
    slugs.forEach(function(slug){
      const meta = slugMap[slug];
      const label = meta ? meta.name : slug;
      $select.append($('<option/>').attr('value', slug).text(label));
    });
    $('#tag-remove-target-count').text(userIds.length);
    $('#tag-remove-confirm').data('targetUserIds', userIds);
    const modal = new bootstrap.Modal('#tag-remove-modal', {});
    modal.show();
  }

  // Bulk API helpers (single request with summary)
  function postAddTaggings(userIds, tagSlug, doneCb) {
    $.ajax({
      url: api_url + '/taggings/?summary=1',
      method: 'POST',
      contentType: 'application/json; charset=utf-8',
      data: JSON.stringify({ tag: { slug: tagSlug }, user_ids: userIds })
    }).done(function(resp){
      // Prefer explicit list from backend; otherwise assume all succeeded
      var okIds = (resp && (resp.created_user_ids || resp.updated_user_ids || resp.user_ids)) || userIds;
      if (!Array.isArray(okIds)) okIds = userIds;
      doneCb(okIds);
    }).fail(function(){ doneCb([]); });
  }
  function deleteTaggings(userIds, tagSlug, doneCb) {
    $.ajax({
      url: api_url + '/taggings/?summary=1',
      method: 'DELETE',
      contentType: 'application/json; charset=utf-8',
      data: JSON.stringify({ user_ids: userIds, tag_slug: tagSlug })
    }).done(function(resp){
      var okIds = (resp && (resp.deleted_user_ids || resp.user_ids)) || userIds;
      if (!Array.isArray(okIds)) okIds = userIds;
      doneCb(okIds);
    }).fail(function(){ doneCb([]); });
  }

  // DataTables instance handle (set after init)
  let dt = null;

  function applyAddedTag(userIds, tagSlug) {
    // Update data model
    const map = getTagMapBySlug();
    userIds.forEach(function(uid){
      const p = participants.find(function(x){ return x.user_id === uid; });
      if (!p) return;
      const slugs = ensureTagSlugs(p);
      if (slugs.indexOf(tagSlug) === -1) slugs.push(tagSlug);
      // If backend returned metadata for new tag, capture it
      if (map[tagSlug]) upsertTagMeta(map[tagSlug]);
    });
    if (dt) {
      // Redraw affected rows' tag cells via invalidation
      userIds.forEach(function(uid){
        const row = dt.row('#participant-' + uid);
        if (row && row.node()) {
          // Force DataTables to re-render the row from data
          dt.row(row).invalidate('data');
        }
      });
      dt.draw(false);
      // Re-init tag buttons/popovers
      try {
        add_colortag_buttons(api_url, document.getElementById('table-participants'), participants);
      } catch (e) {}
    }
  }

  function applyRemovedTag(userIds, tagSlug) {
    userIds.forEach(function(uid){
      const p = participants.find(function(x){ return x.user_id === uid; });
      if (!p) return;
      const slugs = ensureTagSlugs(p);
      p.tag_slugs = slugs.filter(function(s){ return s !== tagSlug; });
    });
    if (dt) {
      userIds.forEach(function(uid){
        const row = dt.row('#participant-' + uid);
        if (row && row.node()) dt.row(row).invalidate('data');
      });
      dt.draw(false);
      try {
        add_colortag_buttons(api_url, document.getElementById('table-participants'), participants);
      } catch (e) {}
    }
  }

  // Safely hide a Bootstrap modal to avoid aria-hidden focus warning
  function hideModalSafely(modalId) {
    try {
      const el = document.getElementById(modalId);
      if (!el) return;
      // If focus is inside the modal, blur it before hiding so aria-hidden won't hide a focused descendant
      if (el.contains(document.activeElement)) {
        try { document.activeElement.blur(); } catch (e) {}
        try { document.body && document.body.focus && document.body.focus(); } catch (e) {}
      }
      const inst = bootstrap.Modal.getInstance(el);
      if (inst) inst.hide();
    } catch (e) {}
  }

  // Apply enrollment status change locally and refresh the row + counters
  function applyEnrollmentStatusChange(userId, newStatusName) {
    try {
      const p = participants.find(function(x){ return x.user_id === userId; });
      if (p) p.enrollment_status = newStatusName;
      if (dt) {
        const row = dt.row('#participant-' + userId);
        if (row && row.node()) dt.row(row).invalidate('data');
        dt.draw(false);
      }
      // Recompute counters
      const counts = participants.reduce(function(acc, curr){ acc[curr.enrollment_status] = (acc[curr.enrollment_status] || 0) + 1; return acc; }, {});
      $('#status-ACTIVE-count').text(counts['ACTIVE'] || 0);
      $('#status-PENDING-count').text(counts['PENDING'] || 0);
      $('#status-REMOVED-count').text(counts['REMOVED'] || 0);
      $('#status-BANNED-count').text(counts['BANNED'] || 0);
    } catch (e) {}
  }

  // Show confirmation modal and perform enrollment removal/ban via API
  function confirm_remove_participant(row, rowRef, statusName, actionLabel) {
    try {
      const isBan = statusName === 'BANNED';
      // Titles
      $('#enrollment-remove-modal-remove-title').toggle(!isBan);
      $('#enrollment-remove-modal-ban-title').toggle(isBan);
      // Descriptions
      $('#enrollment-remove-modal-remove-description').toggle(!isBan);
      $('#enrollment-remove-modal-ban-description').toggle(isBan);
      // Target user text
      var fullName = (row.first_name || '') + ' ' + (row.last_name || '');
      fullName = fullName.trim() || row.username || row.email || String(row.user_id);
      $('#enrollment-remove-modal-user').text(fullName);
      // Configure primary button
      var $btn = $('#enrollment-remove-modal-button');
      $btn.off('click.aplusEnrollRemove').text(actionLabel);
      $btn.on('click.aplusEnrollRemove', function(){
        $btn.prop('disabled', true);
        $.ajax({
          url: api_url + '/students/' + encodeURIComponent(row.user_id) + '/?status=' + encodeURIComponent(statusName),
          method: 'DELETE'
        }).done(function(){
          applyEnrollmentStatusChange(row.user_id, statusName);
          const m = bootstrap.Modal.getInstance(document.getElementById('enrollment-remove-modal'));
          if (m) m.hide();
        }).fail(function(){
          // Silently close; optionally, we could show a toast/alert here
          const m = bootstrap.Modal.getInstance(document.getElementById('enrollment-remove-modal'));
          if (m) m.hide();
        }).always(function(){
          $btn.prop('disabled', false);
        });
      });
      // Show modal
      const modal = new bootstrap.Modal('#enrollment-remove-modal', {});
      modal.show();
    } catch (e) {}
  }

  // Translation helpers for header and reset button
  let aplusTranslationsReady = false;
  function updateHeaderTranslations() {
    try {
      const $thead = $('#table-participants thead');
      if (!$thead.length) return;
      $thead.find('[data-i18n-key]').each(function(){
        const key = $(this).attr('data-i18n-key');
        if (key && typeof _ === 'function') $(this).text(_(key));
      });
      $thead.find('input[placeholder-i18n-key]').each(function(){
        const key = $(this).attr('placeholder-i18n-key');
        if (key && typeof _ === 'function') $(this).attr('placeholder', _(key));
      });
    } catch (e) {}
  }
  function updateResetFiltersButtonText() {
    try {
      if (!dt || typeof dt.button !== 'function' || typeof _ !== 'function') return;
      // Use Buttons selector by name for reliability
      const btn = dt.button('resetFilters:name');
      if (btn && typeof btn.text === 'function') btn.text(_('Reset filters'));
    } catch (e) {}
  }
  function updateResetFiltersButtonTextWithRetry(retries) {
    updateResetFiltersButtonText();
    if (retries <= 0) return;
    setTimeout(function(){ updateResetFiltersButtonTextWithRetry(retries - 1); }, 200);
  }

  // Build DataTables columns and header
  const $table = $('#table-participants');
  if ($table.length) {
    const selectedIds = new Set();

    // Inject sticky header styles (once) and utilities to update sticky offsets
    (function injectStickyHeaderStylesOnce(){
      if (!document.getElementById('aplus-dt-sticky-styles')) {
        const css = [
          // Ensure thead inherits the page background (light/dark friendly)
          '#table-participants thead{background:var(--bs-body-bg);}',
          // Base header row (labels) with no visible divider to the filters row
          '#table-participants thead tr th{position:sticky;top:0;z-index:5;background:var(--bs-body-bg);background-clip:padding-box;border-bottom:0;}',
          // Filter row sticks under labels; nudge by 2px to overlap and eliminate hairline gaps on HiDPI/zoom.
          '#table-participants thead tr.aplus-filters th{top:calc(var(--aplus-dt-header-h,40px) - 2px);z-index:4;background:var(--bs-body-bg);background-clip:padding-box;border-top:0;}',
          // Remove any table border spacing that could create seams
          '#table-participants{--aplus-dt-header-h:40px;border-collapse:separate;border-spacing:0;}',
          // Keep the checkbox column narrow and non-growing
          '#table-participants th.select-box, #table-participants td.select-box{width:2.5rem;max-width:2.5rem;min-width:2rem;}',
        ].join('\n');
        const style = document.createElement('style');
        style.type = 'text/css';
        style.id = 'aplus-dt-sticky-styles';
        style.appendChild(document.createTextNode(css));
        document.head.appendChild(style);
      }
    })();
    function updateStickyOffsets(){
      try {
        const thead = $table.find('thead#table-heading');
        if (!thead.length) return;
        const $labels = thead.find('tr').first();
        // Use outerHeight to include padding/borders
        const h = Math.max(0, Math.round($labels.outerHeight())) || 40;
        $table.get(0).style.setProperty('--aplus-dt-header-h', h + 'px');
      } catch (e) {}
    }

    function renderCheckbox(_data, _type, row) {
      return '<input type="checkbox" name="students" value="' + row.user_id + '">';
    }
    function renderLink(data, _type, row) {
        return '<a href="' + escapeHtml(row.link) + '">' + escapeHtml(data) + '</a>';
    }
    function renderMail(data, _type, row) {
      const text = data || row.username;
      const href = data ? ('mailto:' + data) : '#';
        return '<a href="' + escapeHtml(href) + '">' + escapeHtml(text) + '</a>';
    }

    const columns = (function(){
      const cols = [];
  if (is_teacher) cols.push({ title: '<input type="checkbox" id="students-select-all" aria-label="Select all on page">', data: null, orderable: false, searchable: false, className: 'text-center select-box', width: '2.5rem', render: renderCheckbox });
      cols.push({ title: '<span data-i18n-key="Student ID">Student ID</span>', data: 'id', name: 'StudentID:name', className: "col-1 student-id", render: renderLink, type: 'html' });
      cols.push({ title: '<span data-i18n-key="Last name">Last name</span>', data: 'last_name', className: "col-1 last-name", render: renderLink, type: 'html' });
      cols.push({ title: '<span data-i18n-key="First name">First name</span>', data: 'first_name', className: "col-2 first-name", render: renderLink, type: 'html' });
      cols.push({ title: '<span data-i18n-key="Email">Email</span>', data: 'email', name: 'Email:name', className: "col-2", render: renderMail, type: 'html' });
      cols.push({ title: '<span data-i18n-key="Status">Status</span>', data: 'enrollment_status', className: 'col-1 status', render: function(data, _type, row){ return '<a href="' + escapeHtml(row.link) + '">' + escapeHtml(enrollment_statuses[data]) + '</a>'; }, type: 'html' });
      cols.push({ title: '<span data-i18n-key="Tags">Tags</span>', data: null, className: 'user-tags col-3', render: function(_data, _type, row){ return renderTagsCell(row); }, type: 'html' });
      if (is_teacher) cols.push({ title: '', data: null, orderable: false, searchable: false, className: 'actions-container', type: 'html' });
      return cols;
    })();

    // Ensure a thead exists and contains a filters row cloned from the labels row for perfect alignment
    (function ensureHeaderWithFilters(){
      let $thead = $table.find('thead').first();
      if (!$thead.length) {
        $thead = $('<thead id="table-heading"></thead>');
        const $labels = $('<tr></tr>');
        columns.forEach(function(col){ $labels.append($('<th></th>').html(col.title || '')); });
        $thead.append($labels);
        $table.prepend($thead);
      }
      if (!$thead.attr('id')) $thead.attr('id', 'table-heading');
      if ($thead.find('tr.aplus-filters').length === 0) {
        const $labels = $thead.find('tr').first();
        const $filters = $labels.clone(false).addClass('aplus-filters');
        // Clear label text and insert inputs per column
        $filters.find('th').each(function(idx){
          const $th = $(this);
          $th.removeAttr('aria-sort').removeClass('sorting sorting_asc sorting_desc');
          $th.off(); // no click handlers for sort on filter row
          $th.empty();
          const addInput = (
            (!is_teacher && idx >= 0 && idx <= 4) ||
            (is_teacher && idx >= 1 && idx <= 6)
          );
          if (addInput) {
            const placeholderKey = 'Search';
            const $inp = $('<input type="text" class="form-control form-control-sm" />')
              .attr('data-column', idx)
              .attr('placeholder-i18n-key', placeholderKey)
              .attr('placeholder', placeholderKey);
            $th.append($inp);
          }
        });
        $thead.append($filters);
        // Update sticky offset after filters row exists
        try { updateStickyOffsets(); } catch (e) {}
      }
    })();

    // Track translation readiness to update labels after DT builds DOM
    $(document).off('aplus:translation-ready.aplusHead').on('aplus:translation-ready.aplusHead', function(){
      aplusTranslationsReady = true;
      updateHeaderTranslations();
      updateResetFiltersButtonTextWithRetry(20);
    });

    // Language file (Finnish if page lang-fi)
    const pageLanguageUrl = $('body').hasClass('lang-fi') ? 'https://cdn.datatables.net/plug-ins/2.2.1/i18n/fi.json' : '';

    // Determine Tags column index for exports
    const tagsColIndex = is_teacher ? 6 : 5;

    function removeHtmlFromColumns(data, row, column/*, node */) {
      if (typeof data === 'string') {
        return column === tagsColIndex
          ? data.replace(/(<[^>]*>)+/g, ',').slice(1,-1)
          : $.fn.dataTable.util.stripHtml(data);
      }
      return data;
    }

    var buttonCommon = {
      exportOptions: {
        columns: ':visible:not(.actions-container)',
        format: { body: removeHtmlFromColumns }
      }
    };

    function clearSearch() {
      try {
        $table.find('thead#table-heading input[type="text"]').val('');
        const $global = $table.closest('.dataTables_wrapper').find('div.dataTables_filter input[type="search"], div.dataTables_filter input[type="text"]');
        $global.val('');
        $('.filter-users button').each(function(){ $(this).find('i').removeClass('bi-check-square').addClass('bi-square'); });
        // Set Active status as checked by default
        $('.filter-users button.filter-status[data-status="ACTIVE"]').find('i').removeClass('bi-square').addClass('bi-check-square');
        recomputeFilters();
      } catch (e) {}
      try {
        if ($.fn.dataTable && $.fn.dataTable.isDataTable($table)) {
          const api = $table.DataTable();
          api.search('');
          api.columns().search('');
          api.draw(false);
        }
      } catch (e) {}
    }

    // Initialize DataTables
    dt = $table.DataTable({
      data: participants,
      columns: columns,
      order: [[ is_teacher ? 1 : 0, 'asc' ]],
      orderCellsTop: true,
      stateSave: true,
      stateSaveCallback: function(settings, data) {
        localStorage.setItem('participantsListPageLength', data.length);
      },
      rowId: function(row) { return 'participant-' + row.user_id; },
      headerCallback: function(thead /*, data, start, end, display */) {
        // Ensure thead has id and filters row exists even if DT rebuilt the header
        try {
          const $thead = $(thead);
          if (!$thead.attr('id')) $thead.attr('id', 'table-heading');
          if ($thead.find('tr.aplus-filters').length === 0) {
            const $labels = $thead.find('tr').first();
            const $filters = $labels.clone(false).addClass('aplus-filters');
            $filters.find('th').each(function(idx){
              const $th = $(this);
              $th.removeAttr('aria-sort').removeClass('sorting sorting_asc sorting_desc');
              $th.off();
              $th.empty();
              const addInput = (
                (!is_teacher && idx >= 0 && idx <= 4) ||
                (is_teacher && idx >= 1 && idx <= 6)
              );
              if (addInput) {
                const placeholderKey = 'Search';
                const $inp = $('<input type="text" class="form-control form-control-sm" />')
                  .attr('data-column', idx)
                  .attr('placeholder-i18n-key', placeholderKey)
                  .attr('placeholder', placeholderKey);
                $th.append($inp);
              }
            });
            $thead.append($filters);
            try { updateHeaderTranslations(); } catch (e) {}
            try { updateStickyOffsets(); } catch (e) {}
          }
        } catch (e) {}
      },
      createdRow: function(row, data) {
        const tagCellIndex = is_teacher ? 6 : 4;
        const $cells = $('td', row);
        $($cells.get(tagCellIndex)).addClass('usertags-container').attr('data-user-id', data.user_id);
        $(row).attr('data-user-id', data.user_id);
      },
      lengthMenu: [[10, 50, 100, 500, -1], [10, 50, 100, 500, 'All']],
      pageLength: localStorage.getItem('participantsListPageLength') ? parseInt(localStorage.getItem('participantsListPageLength'), 10) : 50,
      deferRender: true,
      autoWidth: false,
      language: { url: pageLanguageUrl },
      initComplete: function(){
        if (aplusTranslationsReady) {
          try { updateHeaderTranslations(); } catch (e) {}
          try { updateResetFiltersButtonText(); } catch (e) {}
        }
        // If the second header row (filters) was removed/rebuilt by DT, ensure it exists
        try {
          const $thead = $table.find('thead#table-heading');
          if ($thead.length && $thead.find('tr.aplus-filters').length === 0) {
            const $filters = $('<tr class="aplus-filters"></tr>');
            const colCount = this.api().columns().count();
            for (let idx = 0; idx < colCount; idx++) {
              const $thFilter = $('<th></th>');
              const addInput = (
                (!is_teacher && idx >= 0 && idx <= 4) ||
                (is_teacher && idx >= 1 && idx <= 6)
              );
              if (addInput) {
                const placeholderKey = 'Search';
                const $inp = $('<input type="text" class="form-control form-control-sm" />')
                  .attr('data-column', idx)
                  .attr('placeholder-i18n-key', placeholderKey)
                  .attr('placeholder', placeholderKey);
                $thFilter.append($inp);
              }
              $filters.append($thFilter);
            }
            $thead.append($filters);
            // Re-apply translations for placeholders
            try { updateHeaderTranslations(); } catch (e) {}
            try { updateStickyOffsets(); } catch (e) {}
          }
        } catch (e) {}
      },
      dom: "<'row'<'col-md-3 col-sm-6'l><'col-md-5 col-sm-6'B><'col-md-4 col-sm-12'f>>" +
           "<'row'<'col-sm-12 mt-3'i>>" +
           "<'row'<'#table-participants-div.col-sm-12'tr>>" +
           "<'row'<'col-sm-5'i><'col-sm-7'p>>",
      buttons: [
        $.extend(true, {}, buttonCommon, { extend: 'csvHtml5', className: 'btn-sm' }),
        $.extend(true, {}, buttonCommon, { extend: 'copyHtml5', className: 'btn-sm' }),
        $.extend(true, {}, buttonCommon, { extend: 'excelHtml5', className: 'btn-sm' }),
        { text: 'Reset filters', className: 'btn-reset-filters btn-sm', name: 'resetFilters', action: function(){ clearSearch(); } }
      ]
    });

    // Keep sticky offset up-to-date on draw, column sizing and window resize
    if (dt && typeof dt.on === 'function') {
      dt.on('draw.aplusSticky column-sizing.aplusSticky', function(){
        try { updateStickyOffsets(); } catch (e) {}
      });
    }
    (function(){
      let _stickyResizeTimer;
      $(window).off('resize.aplusSticky').on('resize.aplusSticky', function(){
        clearTimeout(_stickyResizeTimer);
        _stickyResizeTimer = setTimeout(function(){ try { updateStickyOffsets(); } catch (e) {} }, 100);
      });
    })();

    // Initialize status counters (totals)
    (function(){
      try {
        const counts = participants.reduce(function(acc, curr){ acc[curr.enrollment_status] = (acc[curr.enrollment_status] || 0) + 1; return acc; }, {});
        $('#status-ACTIVE-count').text(counts['ACTIVE'] || 0);
        $('#status-PENDING-count').text(counts['PENDING'] || 0);
        $('#status-REMOVED-count').text(counts['REMOVED'] || 0);
        $('#status-BANNED-count').text(counts['BANNED'] || 0);
      } catch (e) {}
    })();

    // Column search inputs with debounce
    (function(){
      function debounce(fn, delay){ let t; return function(){ const ctx=this, args=arguments; clearTimeout(t); t=setTimeout(function(){ fn.apply(ctx,args); }, delay); }; }
      const doSearch = debounce(function(input){ const $inp=$(input); const colIdx=parseInt($inp.data('column'),10); const val=$inp.val(); if(!isNaN(colIdx)) dt.column(colIdx).search(val).draw(false); }, 200);
      $table.on('input.aplusDTsearch change.aplusDTsearch', 'thead input[type="text"]', function(){ doSearch(this); });
      $table.on('click.aplusDTstop mousedown.aplusDTstop mouseup.aplusDTstop dblclick.aplusDTstop keydown.aplusDTstop','thead input, thead select',function(e){ e.stopPropagation(); });
      const theadEl=$table.find('thead').get(0);
      if (theadEl && theadEl.addEventListener) {
        const stopIfFilterCtrl=function(e){ const t=e.target; if(t && (t.closest && t.closest('input, select, textarea'))) { if (typeof e.stopImmediatePropagation==='function') e.stopImmediatePropagation(); e.stopPropagation(); } };
        ['click','mousedown','mouseup','dblclick','keydown','pointerdown','touchstart'].forEach(function(ev){ theadEl.addEventListener(ev, stopIfFilterCtrl, true); });
      }
    })();

    // Cached filter state
    let currentFilterTags = [];
    let currentFilterStatuses = [];
    function recomputeFilters() {
      currentFilterTags = $('.filter-users button.filter-tag').filter(function(){ return $(this).find('i').hasClass('bi-check-square'); }).map(function(){ return $(this).attr('data-tagslug'); }).get();
      currentFilterStatuses = $('.filter-users button.filter-status').filter(function(){ return $(this).find('i').hasClass('bi-check-square'); }).map(function(){ return $(this).attr('data-status'); }).get();
    }
    recomputeFilters();

    const filterFn = function(settings, _data, dataIndex) {
      if (settings.nTable !== $table.get(0)) return true;
      const rowData = dt.row(dataIndex).data();
      // Normalize slugs by mapping from tag_ids as needed
      if (!Array.isArray(rowData.tag_slugs) || !rowData.tag_slugs.length) ensureTagSlugs(rowData);
      const intersectTags = (rowData.tag_slugs || []).filter(function (tag) { return currentFilterTags.indexOf(tag) >= 0; });
      const tagsOk = intersectTags.length === currentFilterTags.length;
      const statusOk = (currentFilterStatuses.length === 0) || (currentFilterStatuses.indexOf(rowData.enrollment_status) >= 0);
      return tagsOk && statusOk;
    };
    if (!$table.data('aplusFilterRegistered')) {
      $.fn.dataTable.ext.search.push(filterFn);
      $table.data('aplusFilterRegistered', true);
    }

    $('.filter-users button').off('click.aplusFilters').on('click.aplusFilters', function(event){
      event.preventDefault();
      var icon = $(this).find('i');
      if (icon.hasClass('bi-square')) icon.removeClass('bi-square').addClass('bi-check-square');
      else icon.removeClass('bi-check-square').addClass('bi-square');
      recomputeFilters();
      if (dt._aplusRedrawTimer) clearTimeout(dt._aplusRedrawTimer);
      dt._aplusRedrawTimer = setTimeout(function(){ dt.draw(false); }, 0);
      try { const tip = bootstrap.Tooltip && bootstrap.Tooltip.getInstance(this); if (tip) tip.hide(); } catch (e) {}
    });

    initFilterButtonDescriptions();

    // Selection (teacher only)
    if (is_teacher) {
      function filteredUserIds() {
        const data = dt.rows({ search: 'applied', page: 'current' }).data();
        const ids = []; for (let i=0;i<data.length;i++) ids.push(data[i].user_id); return ids;
      }
      function updateHeaderAndGlobal() {
        const ids = filteredUserIds();
        let selectedFiltered = 0; ids.forEach(function(id){ if (selectedIds.has(id)) selectedFiltered++; });
        const totalFiltered = ids.length;
        const allChecked = totalFiltered > 0 && selectedFiltered === totalFiltered;
        const atLeastOne = selectedFiltered > 0 && selectedFiltered < totalFiltered;
        const $all_box = $('#students-select-all');
        $all_box.prop('checked', allChecked).prop('indeterminate', atLeastOne);
        $('#selected-number').text(selectedFiltered);
        $('#add-tag-selected, #remove-tag-selected').prop('disabled', selectedFiltered === 0);
      }
      // Toggle per-row checkbox updates selection store
      $table.on('change', 'input[type="checkbox"][name="students"]', function(){
        const uid = parseInt(this.value, 10);
        if (this.checked) selectedIds.add(uid); else selectedIds.delete(uid);
        updateHeaderAndGlobal();
      });
      // Select all visible rows on the current page only
      $table.off('change.aplusSelectAll', '#students-select-all').on('change.aplusSelectAll', '#students-select-all', function(){
        const $all_box = $(this);
        const ids = filteredUserIds();
        if ($all_box.prop('checked')) ids.forEach(function(id){ selectedIds.add(id); });
        else ids.forEach(function(id){ selectedIds.delete(id); });
        $(dt.rows({ page: 'current' }).nodes()).find('input[type="checkbox"][name="students"]').each(function(){
          const uid = parseInt(this.value, 10);
          $(this).prop('checked', selectedIds.has(uid));
        });
        updateHeaderAndGlobal();
        return false;
      });
      // On every draw, sync checkboxes to selection store and update header/global
      dt.on('draw', function(){
        $(dt.rows({ page: 'current' }).nodes()).find('input[type="checkbox"][name="students"]').each(function(){
          const uid = parseInt(this.value, 10);
          $(this).prop('checked', selectedIds.has(uid));
        });
        updateHeaderAndGlobal();
      });
    }

    // After translations are ready, init tag popovers/buttons and actions
    $(document).off('aplus:translation-ready.aplusTags').on('aplus:translation-ready.aplusTags', function(){
      try { add_colortag_buttons(api_url, document.getElementById('table-participants'), participants); } catch (e) {}
      if (dt && typeof dt.on === 'function' && !dt._aplusTagDrawHandler) {
        dt.on('draw.aplusTagPopovers', function(){
          try { add_colortag_buttons(api_url, document.getElementById('table-participants'), participants); } catch (e) {}
        });
        dt._aplusTagDrawHandler = true;
      }
      if (is_teacher) {
        const renderActionBtn = function(label, icon, onClick, extraClasses, disabled){
          const $btn = $('<button></button>')
            .append($('<i></i>').addClass('bi-' + icon).attr('aria-hidden', true))
            .append(' ' + label)
            .addClass((extraClasses || 'aplus-button--danger aplus-button--xs'))
            .prop('disabled', !!disabled);
          if (!disabled) $btn.on('click', onClick);
          return $btn;
        };
        dt.on('draw.aplusActions', function(){
          dt.rows({page:'current'}).every(function(){
            const row = this.data();
            const $node = $(this.node());
            const $cell = $node.find('td.actions-container');
            const rowRef = $node; // for closures
            const actions = $('<div/>');
            const isTerminal = row.enrollment_status === 'REMOVED' || row.enrollment_status === 'BANNED';
            actions.append(
              renderActionBtn(_('Remove'), 'x-lg', function(){
                confirm_remove_participant(row, rowRef, 'REMOVED', _('Remove'));
              }, undefined, isTerminal)
            ).append(' ').append(
              renderActionBtn(_('Ban'), 'ban', function(){
                confirm_remove_participant(row, rowRef, 'BANNED', _('Ban'));
              }, undefined, isTerminal)
            );
            $cell.empty().append(actions);
            // Add "Add tag" inline button into the Tags column
            const $tagsCell = $node.find('td.usertags-container');
            if ($tagsCell.length && !$tagsCell.find('.add-tag-inline').length) {
              const $btn = $('<button type="button" />')
                .addClass('add-tag-inline aplus-button--secondary aplus-button--xs ms-1')
                .append($('<i/>').addClass('bi-tag').attr('aria-hidden', true))
                .append(' ' + _('Add new tagging'))
                .on('click', function(){ openAddTagModal([row.user_id]); });
              $tagsCell.append(' ').append($btn);
            }
          });
        });
        dt.draw(false);
        // Global "Add tag to selected" button
        $('#add-tag-selected').off('click.aplusAddSel').on('click.aplusAddSel', function(){
          const ids = [];
          const filtered = dt.rows({ search: 'applied', page: 'all' }).data();
          for (let i = 0; i < filtered.length; i++) {
            const uid = filtered[i].user_id;
            if (selectedIds.has(uid)) ids.push(uid);
          }
          if (ids.length) openAddTagModal(ids);
        });
        // Global "Remove tag from selected" button
        $('#remove-tag-selected').off('click.aplusRmSel').on('click.aplusRmSel', function(){
          const ids = [];
          const filtered = dt.rows({ search: 'applied', page: 'all' }).data();
          for (let i = 0; i < filtered.length; i++) {
            const uid = filtered[i].user_id;
            if (selectedIds.has(uid)) ids.push(uid);
          }
          if (ids.length) openRemoveTagModal(ids);
        });
      }
    });

    // Tags changed elsewhere -> refresh filtering
    $(document).off('aplus:tags-changed.aplusDT').on('aplus:tags-changed.aplusDT', function(){
      if (dt._aplusRedrawTimer) clearTimeout(dt._aplusRedrawTimer);
      dt._aplusRedrawTimer = setTimeout(function(){ dt.draw(false); }, 0);
    });

    // Confirm add/remove tag modals (DT path)
    $('#tag-add-confirm').off('click.aplusConfirm').on('click.aplusConfirm', function(){
      const userIds = $(this).data('targetUserIds') || [];
      const tagSlug = $('#tag-add-select').val();
      if (!tagSlug || !userIds.length) return;
      postAddTaggings(userIds, tagSlug, function(successIds){
        if (Array.isArray(successIds) && successIds.length) applyAddedTag(successIds, tagSlug);
        hideModalSafely('tag-add-modal');
      });
    });
    $('#tag-remove-confirm').off('click.aplusRmConfirmDT').on('click.aplusRmConfirmDT', function(){
      const userIds = $(this).data('targetUserIds') || [];
      const tagSlug = $('#tag-remove-select').val();
      if (!tagSlug || !userIds.length) return;
      deleteTaggings(userIds, tagSlug, function(successIds){
        if (Array.isArray(successIds) && successIds.length) applyRemovedTag(successIds, tagSlug);
        hideModalSafely('tag-remove-modal');
      });
    });

    return; // DT path only
  }

  // No DataTables table found; nothing to initialize
}
