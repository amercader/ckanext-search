# CKAN Query Filters spec

The goal of this specification is to provide a common syntax for defining filters
that need to be applied to queries performed. It is not tied to a particular API
endpoint or search backend, and it aims to be simple and extensible.

## Overview

Filters are always provided as a dictionary or as a list of dictionaries.

When provided as a dictionary, the top level keys can either be:

* A field name
* A top level operator: one of `$or` or `$and`

For example:

```
"filters": {
    "incident": "noise complaint",
    "$or": [
        {"resolution": ["unresolved", "in progress"]},
        {"year": {"gt": 2024}}
    ],
    "sector": [2, 8, 10, {"gte":15, "lte": 30}, 35],
}
```

When provided as a list of dictionaries, these are combined with the OR operator. For instance:

```
"filters": [
    {"field1": "value1"},
    {"field2": "value2"},
]
```

is interpreted as:

```
"filters": {
  "$or": [
    {"field1": "value1"},
    {"field2": "value2"},
  ]
}
```

## Individual filters

Individual filters have the form:

```
  {
    "<field_name>": {"<operator1>" : <value1>, "<operator2>" : <value2>...}
  }

```

Note that fields starting with the character `$` must be escaped with another `$` character, for example a `$AU` field would be given as:

```
filters: {
    "$$AU": {"lt": 150}
}
```

If the operator is omitted, the `eq` (for equality) operator is assumed:

```
  {
    "field1": "value1"
  }

```

is equivalent to:

```
  {
    "field1": {"eq" : "value1"}
  }

```

If filters contain a list of values, the `in` operator is assumed, e.g.:

```
  {
    "field1": ["value1", "value2", "value3"]
  }

```

is interpreted as:

```
  {
    "field1": {"in": ["value1", "value2", "value3"]}
  }

```

## Built-in operators

The following operators are supported by default:

| Notation | Operation                            |
| -------- | ------------------------------------ |
| `eq`     | Equal                                |
| `gt`     | Greater than                         |
| `gte`    | Greater than or equal                |
| `lt`     | Lower than                           |
| `lte`    | Lower than or equal                  |
| `in`     | Matches one of the provided values   |

TODO: Additional operators can be added by plugins

## Top level operators

The following default top operators can be used to combine filters:

| Notation | Operation                                  |
| -------- | ------------------------------------------ |
| `$or`    | logical OR, any of the filters can match   |
| `$and`   | logical AND, all of the filters must match |


Top level operators must always contain lists of at least two filters, i.e. all of the 
following are incorrect:

```
{
  "$or": {"field1": "value1"},
}

{
  "$and": [
    {"field1": "value1"}
  ]
}

{
  "$and": ["value1", "value2", "value3"]
}

```

If a field operation is a lists of values or other field operations, the values are grouped into an "in" field operation and the field operations are ORed together, e.g.:

```
  {
    "year": [1990, 2010, {"gt", 2023}]
  }
```

is equivalent to:

```
  {
    "$or": [
      {"year": {"in": [1990, 2010]}}, 
      {"year": {"gt": 2023}}
    ]
  }
```

Operators inside the same dict are combined with the AND operator, i.e. the following 

```
  {
    "last_name": {"gte" : "Jeong", "lte": "Romano"}
  }
```

is equivalent to:

```
    {
      "$and": [
        {"last_name": {"gte" : "Jeong"}},
        {"last_name": {"lte" : "Romano"}}
      ]
    }

```
