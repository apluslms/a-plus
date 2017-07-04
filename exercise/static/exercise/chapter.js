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
		quiz_success_selector: "#quiz-success",
		message_selector: ".progress-bar",
		message_attr: {
			load: "data-msg-load",
			submit: "data-msg-submit",
			error: "data-msg-error"
		},
		modal_selector: "#page-modal",
	};

	function AplusChapter(element, options) {
		this.element = $(element);
		this.settings = $.extend({}, defaults, options);
		this.ajaxForms = false;
		this.url = null;
		this.modalElement = null;
		this.loader = null;
		this.messages = null;
		this.quizSuccess = null;
		this.init();
	}

	$.extend(AplusChapter.prototype, {

		/**
		 * Constructs contained exercise elements.
		 */
		init: function() {
			this.ajaxForms = window.FormData ? true : false;
			this.url = this.element.attr(this.settings.chapter_url_attr);
			this.modalElement = $(this.settings.modal_selector);
			this.loader = $(this.settings.loader_selector);
			this.messages = this.readMessages();
			this.quizSuccess = $(this.settings.quiz_success_selector);
			this.exercises = this.element
				.find("[" + this.settings.exercise_url_attr + "]")
				.aplusExercise(this);
			this.exercisesIndex = 0;
			this.exercisesSize = this.exercises.size();
			if (this.exercisesSize > 0) {
				this.nextExercise();
			} else {
				$.augmentExerciseGroup($(".exercise-column"));
			}
		},

		nextExercise: function() {
			if (this.exercisesIndex < this.exercisesSize) {
				this.exercises.eq(this.exercisesIndex).aplusExerciseLoad();
				this.exercisesIndex++;
			}
		},

		readMessages: function() {
			var messages = {};
			var text = this.loader.find(this.settings.message_selector);
			for (var key in this.message_attr) {
				messages[key] = text.attr(this.message_attr[key]);
			}
			return messages;
		},

		cloneLoader: function(msgType) {
			return $(this.settings.loading_selector)
				.clone().removeAttr("id").removeClass("hide");
		},

		openModal: function(message) {
			this.modalElement.aplusModal("open", message);
		},

		modalError: function(message) {
			this.modalElement.aplusModal("error", message);
		},

		modalContent: function(content) {
			this.modalElement.aplusModal("content", { content: content });
		},

		modalSuccess: function(exercise, badge) {
			this.modalElement.one("hidden.bs.modal", function(event) {
				$(document.body).animate({
					'scrollTop': exercise.offset().top
				}, 300);
			});
			var content = this.quizSuccess.clone()
				.attr("class", exercise.attr("class"))
				.removeClass("exercise hide")
				.removeAttr("id");
			content.find('.badge-placeholder').empty().append(badge);
			if (badge.hasClass("badge-success") || badge.hasClass("badge-warning")) {
				content.find('.btn-success').css('display', 'block');
			} else {
				content.find('.btn-success').hide();
			}
			this.modalContent(content);
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
	var loadName = "aplusExerciseLoad";
	var defaults = {
		quiz_attr: "data-aplus-quiz",
		ajax_attr: "data-aplus-ajax",
		message_selector: ".progress-bar",
		content_element: '<div class="exercise-content"></div>',
		content_selector: '.exercise-content',
		exercise_selector: '#exercise-all',
		summary_selector: '.exercise-summary',
		response_selector: '.exercise-response',
		navigation_selector: 'ul.nav a[class!="dropdown-toggle"]',
		dropdown_selector: 'ul.nav .dropdown-toggle',
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
		this.messages = {};
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
			this.element.height(this.element.height()).empty();
			this.element.append(this.settings.content_element);
			this.element.append(this.loader);

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
					exercise.chapter.nextExercise();
				})
				.done(function(data) {
					exercise.hideLoader();
					exercise.update($(data));
					if (exercise.quiz) {
						exercise.loadLastSubmission($(data));
					} else {
						exercise.chapter.nextExercise();
					}
				});
		},

		update: function(input) {
			var content = this.element.find(this.settings.content_selector)
				.empty().append(
					input.filter(this.settings.exercise_selector).contents()
				);
			this.element.height("auto");
			this.bindNavEvents();
			this.bindFormEvents(content);
		},

		bindNavEvents: function() {
			var chapter = this.chapter;
			this.element.find(this.settings.navigation_selector).aplusModalLink();
			this.element.find(this.settings.dropdown_selector).dropdown();
			this.element.find('.page-modal').aplusModalLink();
		},

		bindFormEvents: function(content) {
			if (!this.ajax) {
				var forms = content.find("form").attr("action", this.url);
				var exercise = this;
				if (this.chapter.ajaxForms) {
					forms.on("submit", function(event) {
						event.preventDefault();
						exercise.submit(this);
					});
				}
			}
			$.augmentExerciseGroup(content);
			window.postMessage({
				type: "a-plus-bind-exercise",
				id: this.chapterID
			}, "*");
		},

		submit: function(form_element) {
			//$(form_element).find(":input").prop("disabled", true);
			//this.showLoader("submit");
			this.chapter.openModal(this.chapter.messages.submit);
			var exercise = this;
			$.ajax($(form_element).attr("action"), {
				type: "POST",
				data: new FormData(form_element),
				contentType: false,
				processData: false,
				dataType: "html"
			}).fail(function() {
				//$(form_element).find(":input").prop("disabled", false);
				//exercise.showLoader("error");
				this.chapter.modalError(exercise.chapter.messages.error);
			}).done(function(data) {
				//$(form_element).find(":input").prop("disabled", false);
				//exercise.hideLoader();
				var input = $(data);
				if (exercise.quiz) {
					var badge = input.find('.badge').eq(2).clone();
					exercise.update(input);
					exercise.chapter.modalSuccess(exercise.element, badge);
				} else {
					exercise.updateSubmission(input);
				}
			});
		},

		updateSummary: function(input) {
			this.element.find(this.settings.summary_selector)
				.empty().append(
					input.find(this.settings.summary_selector).remove().contents()
				);
			this.bindNavEvents();
		},

		updateSubmission: function(input) {
			this.updateSummary(input);
			this.chapter.modalContent(
				input.filter(this.settings.exercise_selector).contents()
			);

			// Update asynchronous feedback.
			if (typeof($.aplusExerciseDetectWaits) == "function") {
				var exercise = this;
				$.aplusExerciseDetectWaits(function(suburl) {
					$.ajax(suburl).done(function(data) {
						var input2 = $(data);
						var new_badges = input2.find(".badge");
						var old_badges = exercise.element.find(exercise.settings.summary_selector + " .badge");
						old_badges.eq(0).replaceWith(new_badges.eq(0).clone());
						old_badges.eq(2).replaceWith(new_badges.eq(1).clone());
						var content = input2.filter(exercise.settings.exercise_selector).contents();
						if (content.text().trim() == "") {
							exercise.chapter.modalSuccess(exercise.element, new_badges.eq(2).clone());
						} else {
							exercise.chapter.modalContent(content);
						}
					}).fail(function() {
						exercise.chapter.modalError(exercise.chapter.messages.error);
					});
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
							exercise.chapter.nextExercise();
						})
						.done(function(data) {
							exercise.hideLoader();
							var f = exercise.element.find(exercise.settings.response_selector)
								.empty().append(
									$(data).filter(exercise.settings.exercise_selector).contents()
								);
							//f.find("table.submission-info").remove();
							exercise.bindFormEvents(f);
							exercise.chapter.nextExercise();
						});
				} else {
					this.chapter.nextExercise();
				}
			} else {
				this.chapter.nextExercise();
			}
		},

		showLoader: function(messageType) {
			this.loader.show().find(this.settings.message_selector)
				.text(this.chapter.messages[messageType]);
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

	$.fn[loadName] = function() {
		return this.each(function() {
			var exercise = $.data(this, "plugin_" + pluginName);
			if (exercise) {
				exercise.load();
			}
		});
	};

})(jQuery, window, document);

// Construct the page chapter element.
jQuery(function() { jQuery("#exercise-page-content").aplusChapter(); });
