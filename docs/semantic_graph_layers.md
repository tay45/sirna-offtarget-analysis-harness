# Semantic Graph Layers

Runtime consensus edges are placed into separate `networkx.MultiDiGraph` layers:

- provider evidence
- signed causal
- unsigned functional
- contextual
- conflicting

Signed paths are retained only when all path edges belong to the signed causal layer. Other retained paths are classified as unsigned functional or contextual.
