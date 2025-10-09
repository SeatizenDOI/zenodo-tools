DELETE FROM deposit_linestring
WHERE deposit_doi IN (
    SELECT doi
    FROM deposit
    WHERE doi = '14747589'
)
AND footprint_linestring IS NULL;