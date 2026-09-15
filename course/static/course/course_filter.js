$(document).ready(function() {
  const tagCheckboxes = $('#tag-filter-menu input[type="checkbox"]');
  const courseCards = $('.frontpage.card[data-audience]');

  tagCheckboxes.prop('checked', false);

  const audienceMap = {
    '1': ['1'],
    '2': ['2'],
    '3': ['1', '2']
  };

  function applyFilters() {
    const selectedAudiences = $('input[name="audience"]:checked')
      .map(function () {
        return this.value;
      })
      .get();

      courseCards.each(function () {
        const $card = $(this);
        const cardAudience = String($card.data('audience'));

        const cardAudiences = audienceMap[cardAudience] || [];

        const audienceMatch =
          selectedAudiences.length === 0 ||
          selectedAudiences.some(a => cardAudiences.includes(a));

        $card.toggle(audienceMatch);
      });
  }

  tagCheckboxes.on('change', function() {
    applyFilters();
  });
});
