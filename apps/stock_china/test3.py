import adata

#df = adata.stock.market.get_market_concept_min_east()
df = adata.stock.market.all_capital_flow_east()
df.to_csv('concept.csv', encoding='utf8')