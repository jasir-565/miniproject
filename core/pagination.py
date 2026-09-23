from django.core.paginator import Paginator


def page_for(request, queryset, parameter='page'):
    page = Paginator(queryset, 12).get_page(request.GET.get(parameter))
    page.parameter = parameter
    query = request.GET.copy()
    query.pop(parameter, None)
    page.query_prefix = query.urlencode()
    return page
