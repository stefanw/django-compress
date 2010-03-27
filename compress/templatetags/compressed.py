import os

from django import template

from django.conf import settings as django_settings

from compress.conf import settings
from compress.utils import media_root, media_url, needs_update, filter_css, filter_js, get_output_filename, get_version

register = template.Library()

def render_common(template_name, obj, filename, version):
    if settings.COMPRESS:
        filename = get_output_filename(filename, version)

    context = obj.get('extra_context', {})
    if settings.COMPRESS_VERSION and version is not None:
        context.update({"version": version})
    prefix = context.get('prefix', None)
    if filename.startswith('http://'):
        context['url'] = filename
    else:
        context['url'] = media_url(filename, prefix)
        
    return template.loader.render_to_string(template_name, context)

def render_css(css, filename, version=None):
    return render_common(css.get('template_name', 'compress/css.html'), css, filename, version)

def render_js(js, filename, version=None):
    return render_common(js.get('template_name', 'compress/js.html'), js, filename, version)

class CompressedCSSNode(template.Node):
    def __init__(self, name, variable):
        self.name = name
        self.variable = variable

    def render(self, context):
        css_name = template.Variable(self.name).resolve(context)

        try:
            css = settings.COMPRESS_CSS[css_name]
        except KeyError:
            return '' # fail silently, do not return anything if an invalid group is specified

        if settings.COMPRESS:

            version = None

            if settings.COMPRESS_AUTO:
                u, version = needs_update(css['output_filename'], 
                    css['source_filenames'])
                if u:
                    filter_css(css)
            else:
                filename_base, filename = os.path.split(css['output_filename'])
                path_name = media_root(filename_base)
                version = get_version(path_name, filename)
            if self.variable is None:
                return render_css(css, css['output_filename'], version)
            else:
                context[self.variable] = [media_url(css['output_filename'], context.get('prefix', None))]
                return ''
        else:
            # output source files
            if self.variable is None:
                r = ''
                for source_file in css['source_filenames']:
                    r += render_css(css, source_file)
                return r
            else:
                context[self.variable] = [media_url(a_css_file, context.get('prefix', None)) for a_css_file in css['source_filenames']]
                return ''


class CompressedJSNode(template.Node):
    def __init__(self, name, variable):
        self.name = name
        self.variable = variable

    def render(self, context):
        js_name = template.Variable(self.name).resolve(context)

        try:
            js = settings.COMPRESS_JS[js_name]
        except KeyError:
            return '' # fail silently, do not return anything if an invalid group is specified
        
        if 'external_urls' in js:
            r = ''
            for url in js['external_urls']:
                r += render_js(js, url)
            return r
                    
        if settings.COMPRESS:

            version = None

            if settings.COMPRESS_AUTO:
                u, version = needs_update(js['output_filename'], 
                    js['source_filenames'])
                if u:
                    filter_js(js)
            else: 
                filename_base, filename = os.path.split(js['output_filename'])
                path_name = media_root(filename_base)
                version = get_version(path_name, filename)
            if self.variable is None:
                return render_js(js, js['output_filename'], version)
            else:
                context[self.variable] = [media_url(js['output_filename'], context.get('prefix', None))]
                return ''
        else:
            # output source files
            if self.variable is None:
                r = ''
                for source_file in js['source_filenames']:
                    r += render_js(js, source_file)
                return r
            else:
                context[self.variable] = [media_url(a_js_file, context.get('prefix', None)) for a_js_file in js['source_filenames']]
                return ''

#@register.tag
def compressed_css(parser, token):
    message = '%r requires one or three arguments: the name of a group in the COMPRESS_CSS setting [as variable]' % token.split_contents()[0]
    tokens = token.split_contents()
    variable = None
    if len(tokens)==2:
        name = tokens[1]
    elif len(tokens)==4:
        name = tokens[1]
        variable = tokens[3]
    else:
        raise template.TemplateSyntaxError, message
    return CompressedCSSNode(name, variable)
compressed_css = register.tag(compressed_css)

#@register.tag
def compressed_js(parser, token):
    message = '%r requires exactly one or three arguments: the name of a group in the COMPRESS_JS setting [as variable]' % token.split_contents()[0]
    tokens = token.split_contents()
    variable = None
    if len(tokens)==2:
        name = tokens[1]
    elif len(tokens)==4:
        name = tokens[1]
        variable = tokens[3]
    else:
        raise template.TemplateSyntaxError, message
    return CompressedJSNode(name, variable)
compressed_js = register.tag(compressed_js)
