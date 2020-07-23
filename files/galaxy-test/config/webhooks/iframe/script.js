$(document).ready(function() {

	var galaxyRoot = typeof Galaxy != 'undefined' ? Galaxy.root : '/';

	var IframeAppView = Backbone.View.extend({
		el: '#iframe',

		appTemplate: _.template(
            '<div id="webhook-iframe-parent"></div>'
		),

		iframeTemplate: _.template(
			'<div id="iframe-header">' +
				'<div id="iframe-name"><%= title %></div>' +
			'</div>' +
			'<iframe id="webhook-iframe" src="<%= src %>" style="width:100%; height: <%= height %>px; border: none;">'
		),

		initialize: function() {
			var self = this;
			this.$el.html(this.appTemplate());
			this.$iframe = this.$('#webhook-iframe-parent');

			$.getJSON(galaxyRoot + 'api/webhooks/iframe/data', function(data) {
				self.$iframe.html(self.iframeTemplate({src: data.src, height: data.height, title: data.title}));
			});
			return this;
		}

	});

	new IframeAppView();
});
