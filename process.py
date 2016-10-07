import os
import collections

import pandas

def create_history_df(path):
    """
    Process `gene_history.gz` for Project Cognoma. Returns a dataframe which
    maps old GeneIDs to new GeneIDs. GeneIDs are not mapped to themselves, so
    make sure not to filter all genes without an old GeneID when using this
    dataset.
    """
    
    renamer = collections.OrderedDict([
        ('Discontinued_GeneID', 'old_entrez_gene_id'),
        ('GeneID', 'new_entrez_gene_id'),
        ('Discontinue_Date', 'date'),
        ('#tax_id', 'tax_id'),
    ])

    history_df = (
        pandas.read_table(path, compression='gzip', na_values='-')
        [list(renamer)]
        .rename(columns=renamer)
        .query("tax_id == 9606")
        .drop(['tax_id'], axis='columns')
        .dropna(subset=['new_entrez_gene_id'])
        .sort_values('old_entrez_gene_id')
    )
    history_df.new_entrez_gene_id = history_df.new_entrez_gene_id.astype(int)
    
    return history_df

def create_gene_df(path):
    """
    Process `Homo_sapiens.gene_info.gz` for Project Cognoma. Filters genes to
    homo sapiens with `tax_id == 9606` to remove Neanderthals et al.
    """
    
    renamer = collections.OrderedDict([
        ('GeneID', 'entrez_gene_id'),
        ('Symbol', 'symbol'),
        ('description', 'description'),
        ('chromosome', 'chromosome'),
        ('type_of_gene', 'gene_type'),
        ('Synonyms', 'synonyms'),
        ('Other_designations', 'aliases'),
        ('#tax_id', 'tax_id'),
    ])

    gene_df = (pandas.read_table(path, compression='gzip', na_values='-')
        [list(renamer)]
        .rename(columns=renamer)
        .query("tax_id == 9606")
        .drop(['tax_id'], axis='columns')
        .sort_values('entrez_gene_id')
    )
    
    return gene_df

def get_chr_symbol_map(gene_df):
    """
    Create a dataframe for mapping genes to Entrez where all is known is the
    chromosome and symbol. Symbol-chromosome pairs are unique. All approved
    symbols should map and the majority of synonyms should also map. Only
    synonyms that are ambigious within a chromosome are removed. 
    """
    primary_df = gene_df[['entrez_gene_id', 'chromosome', 'symbol']]
    synonyms = (gene_df
        .synonyms.dropna().str.split('|')
        .apply(pandas.Series, 1).stack()
        .rename('symbol')
        .reset_index(level=1, drop=True)
    )
    synonym_df = (gene_df
        [['entrez_gene_id', 'chromosome']]
        .join(synonyms, how='inner')
        .drop_duplicates(['chromosome', 'symbol'], keep=False)
    )
    map_df = (primary_df
        .append(synonym_df)
        .drop_duplicates(subset=['chromosome', 'symbol'], keep='first')
        [['symbol', 'chromosome', 'entrez_gene_id']]
        .sort_values(['symbol', 'chromosome'])
    )
    return map_df


if __name__ == '__main__':
    
    # History mapper
    path = os.path.join('download', 'gene_history.gz')
    history_df = create_history_df(path)
    
    path = os.path.join('data', 'updater.tsv')
    history_df.to_csv(path, index=False, sep='\t')

    # Genes data
    path = os.path.join('download', 'Homo_sapiens.gene_info.gz')
    gene_df = create_gene_df(path)

    path = os.path.join('data', 'genes.tsv')
    gene_df.to_csv(path, index=False, sep='\t')

    # Chromosome-Symbol Map
    map_df = get_chr_symbol_map(gene_df)
    path = os.path.join('data', 'chromosome-symbol-mapper.tsv')
    map_df.to_csv(path, index=False, sep='\t')
