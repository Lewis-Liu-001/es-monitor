from sqlparse import tokens as ttypes
from sqlparse import sql as stypes


def translate_metrics(sql_select):
    metric_request = {}
    metric_selector = {}
    for projection_name, projection in sql_select.projections.iteritems():
        if projection.ttype in (ttypes.Name, ttypes.String.Symbol):
            if not sql_select.group_by.get(projection_name):
                raise Exception('selected field not in group by: %s' % projection_name)
        elif isinstance(projection, stypes.Function):
            request, selector = translate_metric(projection, projection_name)
            if request:
                metric_request[projection_name] = request
            if selector:
                metric_selector[projection_name] = selector
        else:
            raise Exception('unexpected: %s' % repr(projection))
    return metric_request, metric_selector


def translate_metric(sql_function, projection_name):
    if not isinstance(sql_function, stypes.Function):
        raise Exception('unexpected: %s' % repr(sql_function))
    sql_function_name = sql_function.tokens[0].get_name().upper()
    if 'COUNT' == sql_function_name:
        params = list(sql_function.get_parameters())
        if params:
            count_keyword = sql_function.tokens[1].token_next_by_type(0, ttypes.Keyword)
            selector = lambda bucket: bucket[projection_name]['value']
            if count_keyword:
                if 'DISTINCT' == count_keyword.value.upper():
                    request = {'cardinality': {'field': params[0].get_name()}}
                    return request, selector
                else:
                    raise Exception('unexpected: %s' % repr(count_keyword))
            else:
                request = {'value_count': {'field': params[0].get_name()}}
                return request, selector
        else:
            selector = lambda bucket: bucket['doc_count']
            return None, selector
    elif sql_function_name in ('MAX', 'MIN', 'AVG', 'SUM'):
        if len(sql_function.get_parameters()) != 1:
            raise Exception('unexpected: %s' % repr(sql_function))
        selector = lambda bucket: bucket[projection_name]['value']
        request = {sql_function_name.lower(): {'field': sql_function.get_parameters()[0].get_name()}}
        return request, selector
    else:
        raise Exception('unsupported function: %s' % repr(sql_function))
