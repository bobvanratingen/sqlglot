from sqlglot import expressions as exp
from sqlglot.optimizer.normalize import normalized
from sqlglot.optimizer.scope import traverse_scope


def pushdown_predicates(expression):
    """
    Rewrite sqlglot AST to pushdown predicates in FROMS and JOINS

    Example:
        >>> import sqlglot
        >>> sql = "SELECT * FROM (SELECT * FROM x AS x) AS y WHERE y.a = 1"
        >>> expression = sqlglot.parse_one(sql)
        >>> pushdown_predicates(expression).sql()
        'SELECT * FROM (SELECT * FROM x AS x WHERE y.a = 1) AS y WHERE TRUE'

    Args:
        expression (sqlglot.Expression): expression to optimize
    Returns:
        sqlglot.Expression: optimized expression
    """
    for scope in reversed(traverse_scope(expression)):
        where = scope.expression.args.get("where")

        if not where:
            continue

        condition = where.this.unnest()

        if normalized(condition, dnf=True):
            predicates = list(
                condition.flatten() if isinstance(condition, exp.Or) else [condition]
            )
            pushdown = set()

            for a in predicates:
                a_tables = set(exp.column_table_names(a))

                for b in predicates:
                    a_tables = a_tables & set(exp.column_table_names(b))

                pushdown.update(a_tables)

            for table in sorted(pushdown):
                source = scope.sources[table]
                if isinstance(source, exp.Table):
                    node = source.find_ancestor(exp.Join, exp.From)
                else:
                    node = source.expression

                for predicate in predicates:
                    new_condition = exp.and_(exp.TRUE)
                    for column in predicate.find_all(exp.Column):
                        if column.text("table") == table:
                            condition = column.find_ancestor(exp.Condition)
                            if isinstance(node, exp.Join):
                                condition.replace(exp.TRUE)
                                new_condition = new_condition.and_(condition)
                            print(new_condition.sql())

                    if isinstance(node, exp.Join):
                        on = node.args.get("on")
                        node.set("on", exp.or_(on, new_condition) if on else new_condition)





        else:
            predicates = list(
                condition.flatten() if isinstance(condition, exp.And) else [condition]
            )

        #for predicate in predicates:
        #    print(predicate.sql())
        #    sources = [
        #        scope.sources.get(table) for table in exp.column_table_names(predicate)
        #    ]

        #    if len(sources) != 1:
        #        continue

        #    source = sources[0]

        #    if isinstance(source, exp.Table):
        #        node = source.find_ancestor(exp.Join, exp.From)

        #        if isinstance(node, exp.Join):
        #            predicate.replace(exp.TRUE)
        #    elif source:
        #        node = source.expression
        #        predicate.replace(exp.TRUE)

        #        aliases = {}

        #        for select in source.selects:
        #            if isinstance(select, exp.Alias):
        #                aliases[select.alias] = select.this
        #            else:
        #                aliases[select.name] = select

        #        def replace_alias(column):
        #            # pylint: disable=cell-var-from-loop
        #            if isinstance(column, exp.Column) and column.name in aliases:
        #                return aliases[column.name]
        #            return column

        #        predicate = predicate.transform(replace_alias)
        #    else:
        #        continue

        #    if isinstance(node, exp.Join):
        #        on = node.args.get("on")
        #        node.set("on", exp.and_(predicate, on) if on else predicate)
        #    elif isinstance(node, exp.Select):
        #        node.where(predicate, copy=False)

    return expression
