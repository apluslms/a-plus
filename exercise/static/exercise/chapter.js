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
		active_element_attr: "data-aplus-active-element",
		loading_selector: "#loading-indicator",
		quiz_success_selector: "#quiz-success",
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
		this.aeOutputs = {}; // Add active element outputs to chapter so they can be found by id later.
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
			this.loader = $(this.settings.loading_selector);
			this.messages = this.readMessages();
			console.log(this.loader, this.messages);
			this.quizSuccess = $(this.settings.quiz_success_selector);

			// do not include active element inputs to exercise groups
			this.element.find("[" + this.settings.active_element_attr +	"='in']").aplusExercise(this, {input: true});

			this.exercises = this.element
				.find("[" + this.settings.exercise_url_attr + "]")
				.aplusExercise(this);
			this.exercisesIndex = 0;
			this.exercisesSize = this.exercises.length;
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
			for (var key in this.settings.message_attr) {
				messages[key] = this.loader.attr(this.settings.message_attr[key]);
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
		last_submission_selector: 'ul.nav ul.dropdown-menu li:first-child a',
		// For active elements:
		active_element_attr: "data-aplus-active-element",
		ae_result_selector: '.ae_result',
		input: false, // determines whether the active element is an input element or not
	};


	function AplusExercise(element, chapter, options) {
		this.element = $(element);
		this.chapter = chapter;
		this.settings = $.extend({}, defaults, options);
		this.url = null;
		this.quiz = false;
		this.ajax = false;
		this.active_element = false;
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

			// Check if the exercise is an active element.
			this.active_element = (this.element.attr(this.settings.active_element_attr) !== undefined);

			// Add the active element outputs to a list so that the element can be found later
			if (this.active_element && !this.settings.input) this.chapter.aeOutputs[this.chapterID] = this;

			this.loader = this.chapter.cloneLoader();

			this.element.height(this.element.height()).empty();
			this.element.append(this.settings.content_element);
			this.element.append(this.loader);

			// Inputs are different from actual exercises and need only be loaded.
			if (this.settings.input) this.load();

			if (!this.active_element && this.ajax) {
			// Add an Ajax exercise event listener to refresh the summary.
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

		// Construct an active element input form
		makeInputForm: function(id, title, type, def_val) {
			var wrap = $("<div>");
			wrap.attr("id", "exercise-all");

			var form = $("<form>");
			form.attr("action", "");
			form.attr("method", "post");

			var first_div = $("<div>");
			first_div.attr("class", "form-group");

			var label = $("<label>");
			label.attr("class", "control-label");
			label.attr("for", id + "_input");
			label.html(title);

			var form_field;
			if (!type) {
				form_field = $("<textarea>");
				form_field.val(def_val);
			} else if (type === "file") {
				form_field = $("<input>");
				form_field.attr("type", "file");
				form.attr("enctype", "multipart/form-data");
			} else if (type.substring(0, 8) == "dropdown") {
				form_field = $("<select>");
				// If the type is dropdown, the format of the type attribute
				// should be "dropdown:option1,option2,option2,.."
				var options = type.split(":").pop().split(",");
				$.each(options, function(i, opt) {
					var option = $("<option>");
					option.text(opt);
					option.val(opt);
					form_field.append(option);
				});
			}

			form_field.attr("class", "form-control");
			form_field.attr("id", id + "_input_id");
			form_field.attr("name", id + "_input");

			var second_div = $("<div>");
			first_div.attr("class", "form-group");

			var button = $("<input>");
			button.attr("class", "btn btn-primary");
			button.attr("value", "Submit");
			button.attr("type", "submit");

			$(first_div).append(label, form_field);
			$(second_div).append(button);
			$(form).append(first_div, second_div);
			$(wrap).append(form);

			return $(wrap);
		},

		load: function() {
			this.showLoader("load");
			var exercise = this;

			if (exercise.settings.input) {
				var title = exercise.element.data("title");
				var type = exercise.element.data("type");
				var def_val = exercise.element.data("default");

				if (!title) title = '';
				if (!def_val) def_val = '';

				exercise.hideLoader();
				var input_form = exercise.makeInputForm(exercise.chapterID, title, type, def_val);
				exercise.update(input_form);
				exercise.loadLastSubmission(input_form);
				exercise.chapter.nextExercise();
			 } else {
				$.ajax(this.url, {dataType: "html"})
					.fail(function() {
						exercise.showLoader("error");
						exercise.chapter.nextExercise();
					})
					.done(function(data) {
						exercise.hideLoader();
						exercise.update($(data));
						if (exercise.quiz || exercise.active_element) {
							exercise.loadLastSubmission($(data));
						} else {
							exercise.chapter.nextExercise();
						}
					 });
				}
		},

		update: function(input) {
			var exercise = this;
			input = input.filter(exercise.settings.exercise_selector).contents();
			var content = exercise.element.find(exercise.settings.content_selector)
				.empty().append(input).hide();

			if (exercise.active_element) {
				var title = "";
				if (exercise.element.attr("data-title"))
					title = "<p><b>" + exercise.element.attr("data-title") + "</b></p>";
				exercise.element.find(exercise.settings.summary_selector).remove();
				$(title).prependTo(exercise.element.find(".exercise-response"));
			}

			content.show();

			// Active element can have height settings in the A+ exercise div that need to be
			// attached to correct DOM-elements before setting the exercise container div height to auto
			var cur_height = exercise.element.css('height');
			if (exercise.active_element) {
				if (exercise.settings.input) {
					$("#" + exercise.chapterID + " textarea").css("height", cur_height);
				} else {
					if (typeof $("#" + exercise.chapterID).data("scale") != "undefined") {
						var cont_height = $(exercise.settings.ae_result_selector, exercise.element)[0].scrollHeight;
						$(exercise.settings.ae_result_selector, exercise.element).css({ "height" : cont_height +"px"});
					} else {
						$(exercise.settings.ae_result_selector, exercise.element).css("height", cur_height);
					}
				}
			}

			this.element.height("auto");
			this.bindNavEvents();
			this.bindFormEvents(content);
		},

		bindNavEvents: function() {
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

		// Submit the formData to given url and then execute the callback.
		submitAjax: function(url, formData, callback, retry) {
			var exercise = this;
			$.ajax(url, {
				type: "POST",
				data: formData,
				contentType: false,
				processData: false,
				dataType: "html"
			}).fail(function(xhr, textStatus, errorThrown) {
				// Retry a few times if submission is not successful
				retry = retry || 0;
				if (xhr.status !== 200 && retry < 5) {
					setTimeout(
						function() {
							exercise.submitAjax(url, formData, callback, retry + 1);
						}, 100);
				}
				//$(form_element).find(":input").prop("disabled", false);
				//exercise.showLoader("error");

				if (!exercise.active_element) {
					exercise.chapter.modalError(exercise.chapter.messages.error);
				} else {
					// active elements don't use loadbar so the error message must be shown
					// in the element container
					var feedback = $("<div>");
					feedback.attr('id', 'feedback');			
					feedback.append(exercise.chapter.messages.error);
					exercise.updateOutput(feedback);
				}
			}).done(function (data) {
				callback(data);
			});
		},

		// Construct form data from input element values
		collectFormData: function(output, form_element) {
			output = $(output);

			var [exercise, inputs, expected_inputs] = this.matchInputs(output);
			// Form data to be sent for evaluation
			var formData = new FormData();
			var input_id = this.chapterID;
			var valid = true;

			$.each(inputs, function(i, id) {
				var input_val;
				var input_elem = $.find("#" + id);

				// Input can be also an output element, in which case the content must be
				// retrieved differently
				if (input_elem[0].hasAttribute("data-inputs")) {

					// If an output uses another output as an input, the output used as an input can
					// be in evaluation which means this output cannot be evaluated yet
					if ($(input_elem).data("evaluating")) {
						valid = false;
						formData = false;
						return;
					}

					input_val = $(input_elem).find(".ae_result").text().trim();

				} else if ($(input_elem).data("type") === "file") {
					input_val = $("#" + id + "_input_id").get(0).files[0];

				} else if (id !== input_id) {
					// Because changing an input value without submitting said input is possible,
					// use the latest input value that has been submitted before for other inputs
					// than the one being submitted now.
					input_val = $(input_elem).data("value");
					// Update the input box back to the value used in evaluation
					$("#" + id + "_input_id").val(input_val);
				} else {
					input_val = $("#" + id + "_input_id").val();
					// Update the saved value data
					$(input_elem).data("value", input_val);
				}
				if (!input_val) valid = false;
				if (formData) formData.append(expected_inputs[i], input_val);
			});

			return [exercise, valid, formData];
		},

		submit: function(form_element) {
			var input = this;
			var chapter = this.chapter;
			if (this.active_element) {
				var input_id = this.chapterID;
				// For every output related to this input, try to evaluate the outputs
				var outputs = $.find('[data-inputs~="' + input_id + '"]');

				$.each(outputs,	function(i, element) {
					var [exercise, valid, formData] = input.collectFormData(element, form_element);
					var output_id = exercise.chapterID;
					var output = $("#" + output_id);
					var out_content = output.find(exercise.settings.ae_result_selector);
					// Indicates that one of inputs has not finished evaluation
					if (!valid && !formData) {
						return; // TODO should this do something else?
					}

					if (!valid) {
						$("#" + output_id).find(exercise.settings.ae_result_selector)
							.html('<p style="color:red;">Fill out all the inputs</p>');
						return;
					}

					output.data('evaluating', true);
					// If the element has no height defined it should keep the height it had with content
					if (typeof output.data("scale") != "undefined") {
						out_content.css({ 'height' : (out_content.height())});
					}
					out_content.html("<p>Evaluating</p>");

					var url = exercise.url;
					exercise.submitAjax(url, formData, function(data) {
						var content = $(data);

						if (! content.find('.alert-danger').length) {
							var poll_url = content.find(".exercise-wait").attr("data-poll-url");
							output.attr('data-poll-url', poll_url);

							exercise.updateSubmission(content);
						} else if (content.find('.alert-danger').contents().text()
						.indexOf("The grading queue is not configured.") >= 0) {
							output.find(exercise.settings.ae_result_selector)
							.html(content.find(".alert").text());
							output.find(exercise.settings.ae_result_selector).append(content.find(".grading-task").text());
						} else {
							output.find(exercise.settings.ae_result_selector)
							.html(content.find('.alert-danger').contents());
						}
					});
				});
			} else {
				chapter.openModal(chapter.messages.submit);
				var exercise = this;
				var url = $(form_element).attr("action");
				var formData = new FormData(form_element);

				exercise.submitAjax(url, formData, function(data) {
					//$(form_element).find(":input").prop("disabled", false);
					//exercise.hideLoader();
					var input = $(data);
					if (exercise.quiz) {
						var badge = input.find('.badge').eq(2).clone();
						exercise.update(input);
						chapter.modalSuccess(exercise.element, badge);
					} else {
						exercise.updateSubmission(input);
					}
				});
			}
		},

		// Find for an active element the names of the input fields required and
		// the corresponding names that are used in mooc-grader exercise type config
		matchInputs: function(element) {
			var output_id = element.attr("id");
			var exercise = this.chapter.aeOutputs[output_id];
			// Find the ids of input elements required for this output
			var inputs = element.attr("data-inputs").split(" ");
			// Find the form field names the grader is expecting
			var expected_inputs = element.find(exercise.settings.ae_result_selector).attr("data-expected-inputs");
			// make sure there are expected inputs
			if (expected_inputs) {
				expected_inputs = expected_inputs.trim().split(" ");
				// There might be extra whitespace or line breaks in the expected inputs data-attribute
				// because of how the template is generated
				expected_inputs = $.grep(expected_inputs, function( a ) {
					return a !== "" || a !== "\n";
				});
			} else {
				expected_inputs = [];
			}
			return	[exercise, inputs, expected_inputs];
		},

		updateSummary: function(input) {
			this.element.find(this.settings.summary_selector)
				.empty().append(
					input.find(this.settings.summary_selector).remove().contents()
				);
			this.bindNavEvents();
		},

		updateSubmission: function(input) {
			if (!this.active_element) {
				this.updateSummary(input);
				this.chapter.modalContent(
					input.filter(this.settings.exercise_selector).contents()
				);
			}

			if (typeof($.aplusExerciseDetectWaits) == "function") {
				var exercise = this;
				var id;
				if (this.active_element) id = "#" +	this.chapterID;

				$.aplusExerciseDetectWaits(function(suburl) {
					$.ajax(suburl).done(function(data) {
						if (exercise.active_element) {
							exercise.updateOutput(data);
							exercise.submit(); // Active element outputs can be chained
						} else {
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
						}
					}).fail(function() {
						exercise.chapter.modalError(exercise.chapter.messages.error);
					});
				}, id);
			}
		},

		updateOutput: function(data) {
			// Put data in this output box
			var exercise = this;
			var type = exercise.element.attr("data-type") || "text"; // default output type is text
			var content = $(data);

			// The data organisation is different depending on whether it is a new submission or
			// the latest submission that is loaded back
			if (!content.is("#feedback")) {
				content = content.find("#feedback");
			}

			if (type == "text") {
				content = content.text();
			} else if (type == "image") {
				content = '<img src="data:image/png;base64, ' + content.text() + '" />';
			}

			var output_container = exercise.element.find(exercise.settings.ae_result_selector);
			output_container.html(content);
			exercise.element.data('evaluating', false);
			// Some result divs should scale to match the content
			if (typeof exercise.element.data("scale") != "undefined" ) {
				output_container.css({ "height" : "auto"});
			}
		},

		// Retrieve and update latest values of the input elements related to this element
		updateInputs: function(data) {
			data = data.submission_data;
			var exercise = this;
			var [exer, input_list, grader_inputs] = exercise.matchInputs(exercise.element);
			// Submission data can contain many inputs
			$(data).each(function(i, input) {
				var grader_id = input[0];
				var input_id = input_list[$.inArray(grader_id, grader_inputs)];
				var input_data = input[1];
				if ($("#" + input_id).data("type") !== "file") {
					// Store the value of the input to be used later for submitting active
					// element evaluation requests
					$($.find("#" + input_id)).data("value", input_data);
					$("#" +input_id + "_input_id").val(input_data);
				}
			});
		},

		loadLastSubmission: function(input) {
			var link = input.find(this.settings.last_submission_selector);
			var exercise = this;
			if (link.length > 0) {
				var url = link.attr("href");

				if (url && url !== "#") {
					var data_type = "html";
					if (exercise.active_element) {
						// Active element input values are retrieved from the API, so
						// we must extract the submission number from the submission url
						var submission = url.match(/submissions\/\d+/)[0].split('/')[1];
						url = '/api/v2/submissions/' + submission;
						data_type = "json";
					}

					this.showLoader("load");
					$.ajax(url, {dataType: data_type})
						.fail(function() {
							exercise.showLoader("error");
						})
						.done(function(data) {
							exercise.hideLoader();

							if (!exercise.active_element) {
								var f = exercise.element.find(exercise.settings.response_selector)
								.empty().append(
										$(data).filter(exercise.settings.exercise_selector).contents()
									);
								//f.find("table.submission-info").remove();
								exercise.bindFormEvents(f);
							} else {
								// Update the output box values
								exercise.updateOutput(data.feedback);

								// Update the input values
								exercise.updateInputs(data);
							}
						});
				}
			}
			exercise.chapter.nextExercise();
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
