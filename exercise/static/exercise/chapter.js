/**
 * Chapter element containing number of exercise elements.
 *
 */
;(function($, window, document, undefined) {
	"use strict";

	var pluginName = "aplusChapter";
	var defaults = {
		chapter_url_attr: "data-aplus-chapter",
		exercise_url_attr: "data-aplus-exercise",
		loading_selector: "#loading-indicator",
		modal_selector: "#embed-modal",
		modal_content_selector: ".modal-body"
	};

	function AplusChapter(element, options) {
		this.element = $(element);
		this.settings = $.extend({}, defaults, options);
		this.ajaxForms = false;
		this.url = null;
		this.modalElement = null;
		this.init();
	}

	$.extend(AplusChapter.prototype, {

		/**
		 * Constructs contained exercise elements.
		 */
		init: function() {
			this.ajaxForms = window.FormData ? true : false;
			this.url = this.element.attr(this.settings.chapter_url_attr);
			this.modalElement = $(this.settings.modal_selector).modal({show: false});

			this.element.find("[" + this.settings.exercise_url_attr + "]")
				.each(function(index) {
					$(this).attr("id", "chapter-exercise-" + (index + 1));
				})
				.aplusExercise(this);
		},

		cloneLoader: function(msgType) {
			return $(this.settings.loading_selector)
				.clone().removeAttr("id").removeClass("hide");
		},

		openModalURL: function(sourceURL) {
			if (sourceURL && sourceURL !== "#") {
				var self = this;
				$.ajax(sourceURL).done(function(data) {
					self.openModal($(data).filter('table,#exercise'));
				}).fail(function() {
					self.openModal("Internal error.");
				});
			}
		},

		openModal: function(content) {
			this.modalElement.find(this.settings.modal_content_selector)
				.empty().append(content)
				.find('.file-modal').aplusFileModal();
			this.modalElement.modal("show");
		}
	});

	$.fn[pluginName] = function(options) {
		return this.each(function() {
			if (!$.data(this, "plugin_" + pluginName)) {
				$.data(this, "plugin_" + pluginName, new AplusChapter(this, options));
			}
		});
	};

})(jQuery, window, document);

/**
 * Exercise element inside chapter.
 *
 */
;(function($, window, document, undefined) {
	"use strict";

	var pluginName = "aplusExercise";
	var defaults = {
		quiz_attr: "data-aplus-quiz",
		ajax_attr: "data-aplus-ajax",
		message_selector: ".progress-bar",
		message_attr: {
			load: "data-msg-load",
			submit: "data-msg-submit",
			error: "data-msg-error"
		},
		content_element: '<div class="exercise-content"></div>',
		content_selector: '.exercise-content',
		exercise_selector: '#exercise-all',
		summary_selector: '.exercise-summary',
		response_selector: '.exercise-response',
		navigation_selector: 'ul.nav a[class!="dropdown-toggle"]',
		last_submission_selector: 'ul.nav ul.dropdown-menu li:first-child a'
	};

	function AplusExercise(element, chapter, options) {
		this.element = $(element);
		this.chapter = chapter;
		this.settings = $.extend({}, defaults, options);
		this.url = null;
		this.quiz = false;
		this.ajax = false;
		this.loader = null;
		this.init();
	}

	$.extend(AplusExercise.prototype, {

		init: function() {
			this.chapterID = this.element.attr("id");
			this.url = this.element.attr(this.chapter.settings.exercise_url_attr);
			this.url = this.url + "?__r=" + encodeURIComponent(
				window.location.href + "#" + this.element.attr("id"));

			// In quiz mode feedback replaces the exercise.
			this.quiz = (this.element.attr(this.settings.quiz_attr) !== undefined);

			// Do not mess up events in an Ajax exercise.
			this.ajax = (this.element.attr(this.settings.ajax_attr) !== undefined);

			this.loader = this.chapter.cloneLoader();
			this.element.append(this.settings.content_element);
			this.element.append(this.loader);
			this.load();

			// Add an Ajax exercise event listener to refresh the summary.
			if (this.ajax) {
				var exercise = this;
				window.addEventListener("message", function (event) {
					if (event.data.type === "a-plus-refresh-stats") {
						$.ajax(exercise.url, {dataType: "html"})
							.done(function(data) {
								exercise.updateSummary($(data));
							});
					}
				});
			}
		},

		load: function() {
			this.showLoader("load");
			var exercise = this;
			$.ajax(this.url, {dataType: "html"})
				.fail(function() {
					exercise.showLoader("error");
				})
				.done(function(data) {
					exercise.hideLoader();
					exercise.update($(data));
					if (exercise.quiz) {
						exercise.loadLastSubmission($(data));
					}
				});
		},

		update: function(input) {
			var content = this.element.find(this.settings.content_selector)
				.empty().append(
					input.filter(this.settings.exercise_selector).contents()
				);
			this.bindNavEvents();
			this.bindFormEvents(content);
		},

		bindNavEvents: function() {
			var chapter = this.chapter;
			this.element.find(this.settings.navigation_selector)
				.on("click", function(event) {
					event.preventDefault();
					chapter.openModalURL($(this).attr("href"));
				});
		},

		bindFormEvents: function(content) {
			var forms = content.find("form").attr("action", this.url);
			var exercise = this;
			if (this.chapter.ajaxForms && !this.ajax) {
				forms.on("submit", function(event) {
					event.preventDefault();
					exercise.submit(this);
				});
			}
			window.postMessage({
				type: "a-plus-bind-exercise",
				id: this.chapterID
			}, "*");
		},

		submit: function(form_element) {
			this.showLoader("submit");
			var exercise = this;
			$.ajax($(form_element).attr("action"), {
				type: "POST",
				data: new FormData(form_element),
				contentType: false,
				processData: false,
				dataType: "html"
			}).fail(function() {
				exercise.showLoader("error");
				$(form_element).find(":input").prop("disabled", false);
			}).done(function(data) {
				exercise.hideLoader();
				if (exercise.quiz) {
					exercise.update($(data));
				} else {
					exercise.updateSubmission($(data));
				}
				$(form_element).find(":input").prop("disabled", false);
			});
			$(form_element).find(":input").prop("disabled", true);
		},

		updateSummary: function(input) {
			this.element.find(this.settings.summary_selector)
				.empty().append(
					input.find(this.settings.summary_selector).contents()
				);
			this.bindNavEvents();
		},

		updateSubmission: function(input) {
			this.updateSummary(input);

			// Open feedback modal.
			this.chapter.openModal(
				input.find(this.settings.response_selector).contents()
			);
			if (typeof($.aplusExerciseDetectWaits) == "function") {
				var exercise = this;
				$.aplusExerciseDetectWaits(function(suburl) {
					exercise.chapter.openModalURL(suburl);
				});
			}
		},

		loadLastSubmission: function(input) {
			var link = input.find(this.settings.last_submission_selector);
			if (link.size() > 0) {
				var url = link.attr("href");
				if (url && url !== "#") {
					this.showLoader("load");
					var exercise = this;
					$.ajax(link.attr("href"), {dataType: "html"})
						.fail(function() {
							exercise.showLoader("error");
						})
						.done(function(data) {
							exercise.hideLoader();
							var f = exercise.element.find(exercise.settings.response_selector)
								.empty().append(data);
							f.find("table.submission-info").remove();
							exercise.bindFormEvents(f);
						});
				}
			}
		},

		showLoader: function(messageType) {
			this.loader.show().find(this.settings.message_selector)
				.text(this.loader.attr(this.settings.message_attr[messageType]));
			if (messageType == "error") {
				this.loader.removeClass("active").addClass("progress-bar-danger");
			} else {
				this.loader.addClass("active").removeClass("progress-bar-danger");
			}
		},

		hideLoader: function() {
			this.loader.hide();
		}
	});

	$.fn[pluginName] = function(chapter, options) {
		return this.each(function() {
			if (!$.data(this, "plugin_" + pluginName)) {
				$.data(this, "plugin_" + pluginName, new AplusExercise(this, chapter, options));
			}
		});
	};

})(jQuery, window, document);

// Construct the page chapter element.
jQuery(function() { jQuery("#exercise").aplusChapter(); });
