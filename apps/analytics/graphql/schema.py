import graphene

from apps.analytics.graphql.queries import Query

schema = graphene.Schema(query=Query)
