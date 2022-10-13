from django.conf import settings
from rest_framework_csv.renderers import CSVRenderer

def remove_newlines(x):
    return x.replace('\n', ' ').replace('\r', '') if isinstance(x, str) else x

class CSVExcelRenderer(CSVRenderer):
    format = 'excel.csv'
    writer_opts = { 'delimiter': settings.EXCEL_CSV_DEFAULT_DELIMITER }

    def flatten_item(self, item):
        "Remove newlines from the item in addition to flattening"
        flat_item = super().flatten_item(item)
        return {k: remove_newlines(v) for k, v in flat_item.items()}

    # pylint: disable-next=dangerous-default-value
    def render(self, data, media_type=None, renderer_context={}, writer_opts=None):
        "Extract sep from GET parameters if specified"
        if 'request' in renderer_context and 'writer_opts' not in renderer_context:
            get = renderer_context['request'].GET
            if 'sep' in get:
                new_writer_opts = {
                    'writer_opts': { 'delimiter': get['sep'] }
                }
                renderer_context.update(new_writer_opts)
        response = super().render(data, media_type, renderer_context, writer_opts)
        return '\uFEFF'.encode('UTF-8') + response
