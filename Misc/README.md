# Misc
Data manipulation and numeric computation that does not fit elsewhere.

* [Natural Number Operation Tree](Natural%20Number%20Operation%20Tree)
  * Generates a pickled Python tree object. As any tree, that object contain relations between nodes. The nodes are either a natural number or an ordered pair of natural numbers. The relations are operations: '+' applied to (2,3) produces (5), '√' applied to (9) produces (3), '**' applied to (3,3) produces (27). All possible relations obtained through some 15 operations are stored in the list. However, excessively large operations are not computed, and as such the tree is bounded and has fit into a 12MB binary file.
