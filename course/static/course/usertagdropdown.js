(function ($) {
  $(document).on('aplus:translation-ready', function() {
    $('.usertags-container').each(function() {
      const $container = $(this);
      const add_text = _("Add new tagging");
      const user_id = $container.data('user-id');
      const tag_ids = $container.find('.colortag').map(function() {
        return $(this).data('tagid');
      }).get();
      const get_users = (typeof get_users_for_user === 'function') ?
        get_users_for_user(user_id) :
        function() { return [user_id]; };
      const add_taggings_id = 'add-taggings-' + user_id;

      create_tagging_dropdown(
        tag_ids,
        get_users,
        add_text,
        add_taggings_id,
        function ($elem) {
          if ($elem.find('.colortag').length > 0)
            $container.append($elem);
        },
        function (jqXHRs, tags_xhr) { tags_xhr.done(function (data_tags) {
          const tags = data_tags.results;
          jqXHRs.forEach(function (jqXHR) {
            jqXHR.done(function (data) {
              const tag = tags.find(function (tag) {
                return tag.id === data.tag.id; });
              $container.find('.dropdown').before(django_colortag_label(tag), ' ');
              if (typeof extra_click_handler === 'function') {
                 extra_click_handler(data);
              }
            });
          });
        });}
      );
    });
  });
})(jQuery);
