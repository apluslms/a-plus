document.addEventListener('aplus:translation-ready', function() {
  document.querySelectorAll('.usertags-container').forEach(function(container) {
    const add_text = "Add new tagging";
    const user_id = container.dataset.userId;
    const tag_ids = Array.from(container.querySelectorAll('.colortag')).map(function(tag) {
      return tag.dataset.tagid;
    });
    const get_users = (typeof get_users_for_user === 'function') ?
      get_users_for_user(user_id) :
      function() { return [user_id]; };
    const add_taggings_id = 'add-taggings-' + user_id;

    create_tagging_dropdown(
      tag_ids,
      get_users,
      add_text,
      add_taggings_id,
      function (elem) {
        if (elem.querySelectorAll('.colortag').length > 0)
          container.appendChild(elem);
      },
      function (jqXHRs, tags_xhr) { tags_xhr.then(function (data_tags) {
        const tags = data_tags.results; //FIXME course tags might be paginated and this only reads the first page
        jqXHRs.forEach(function (jqXHR) {
          jqXHR.then(function (data) {
            const tag = tags.find(function (tag) {
              return tag.id === data.tag.id; });
            // This callback may be called for multiple taggings (because
            // the same tag may be added to multiple students at once), hence
            // the tag must be added to the right container in the DOM.
            const userContainer = document.querySelector('.usertags-container[data-user-id="' + data.user.id + '"]');
            if (userContainer) {
              const dropdown = userContainer.querySelector('.dropdown');
              if (dropdown) {
                dropdown.insertAdjacentHTML('beforebegin', django_colortag_label(tag) + ' ');
              }
            }
            if (typeof extra_click_handler === 'function') {
              extra_click_handler(data);
            }
          });
        });
      });}
    );
  });
});
