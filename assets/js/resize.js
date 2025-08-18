$(function() {
  "use strict";

  $('.resizable-xs, .resizable-sm, .resizable-md, .resizable-lg').aplusResizable();
});

/**
* This plugin makes the children of an element resizable horizontally. It
* creates "handle" elements between the children that the user can click and
* drag to resize its adjacent children.
*
* Usage: add one of the following classes to the parent element: resizable-xs,
* resizable-sm, resizable-md, resizable-lg. The first one, resizable-xs, is
* always resizable. The others have a minimum screen width to be resizable.
* This is useful if you want to display content in resizable columns above a
* certain screen size, and otherwise stack them vertically.
*
* Note: the child elements must have min-width values.
* Note 2: the parent element to resize-handle must have position: relative.
*/
(function($, document) {
  "use strict";

  const pluginName = "aplusResizable";
  var defaults = {};

  function AplusResizable(element, options) {
    this.settings = $.extend({}, defaults, options);
    this.element = $(element);
    this.init();
  }

  $.extend(AplusResizable.prototype, {
    init: function() {
      var resizeIndex = null;
      const container = this.element;
      const children = container.children();

      // Create drag handles between the children.
      children.each(function (i) {
        if (i === children.length - 1) {
          return;
        }
        const handle = $('<div class="resize-handle"></div>');
        // Start resizing when holding down the mouse button.
        function resizeStart() {
          resizeIndex = i;
          $(document.body).css('cursor', 'col-resize');
          $(document.body).css('user-select', 'none');
        };
        handle
          .on('mousedown', resizeStart)
          .on('touchstart', resizeStart);
        $(this).append(handle);
      });

      // Resize when moving the mouse.
      function resizeMove(x) {
        if (resizeIndex === null) {
          return;
        }
        const leftElement = $(children[resizeIndex]);
        const rightElement = $(children[resizeIndex + 1]);
        // The total width available for both left and right child.
        const totalWidth = leftElement.outerWidth(true) + rightElement.outerWidth(true);
        // Calculate new width for the left child based on mouse position.
        var leftWidth = x - leftElement.offset().left;
        // Dragging past the minimum width can cause one of the elements to
        // stretch from the opposite end.
        const leftMinWidth = parseFloat(leftElement.css('min-width'));
        if (leftMinWidth) {
          leftWidth = Math.max(leftWidth, leftMinWidth);
        }
        const rightMinWidth = parseFloat(rightElement.css('min-width'));
        if (rightMinWidth) {
          leftWidth = Math.min(leftWidth, totalWidth - rightMinWidth);
        }
        // Calculate width ratios and set the CSS properties.
        const containerWidth = container.width();
        const leftRatio = leftWidth / containerWidth;
        leftElement.css('flex-basis', leftRatio * 100 + '%');
        const rightRatio = (totalWidth - leftWidth) / containerWidth;
        rightElement.css('flex-basis', rightRatio * 100 + '%');
      };

      // Stop resizing when letting go of the mouse button.
      function resizeEnd() {
        resizeIndex = null;
        $(document.body).css('cursor', '');
        $(document.body).css('user-select', '');
      };

      $(document)
        .on('mousemove', function(event) {
          resizeMove(event.clientX);
        })
        .on('touchmove', function(event) {
          if (event.touches.length === 1) {
            resizeMove(event.touches.item(0).clientX);
          }
        })
        .on('mouseup', resizeEnd)
        .on('touchend', resizeEnd)
        .on('touchcancel', resizeEnd);
    },
  });

  $.fn[pluginName] = function(options) {
    return this.each(function() {
      $.data(this, "plugin_" + pluginName, new AplusResizable(this, options));
    });
  };

})(jQuery, document);
