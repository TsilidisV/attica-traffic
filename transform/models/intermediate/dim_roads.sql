select
    device_id,
    CASE 
        WHEN road_name = 'Β. ΣΟΦΙΑΣ' THEN 'ΒΑΣ. ΣΟΦΙΑΣ'
        WHEN road_name = 'Π. ΡΑΛΛΗ' THEN 'ΠΕΤΡΟΥ ΡΑΛΛΗ'
        WHEN road_name = 'Β. ΑΛΕΞΑΝΔΡΟΥ' THEN 'ΒΑΣ. ΑΛΕΞΑΝΔΡΟΥ'
        WHEN road_name = 'ΕΘΝ. ΑΝΤΙΣΤΑΣΕΩΣ (ΟΛΓΑΣ)' THEN 'ΕΘΝ. ΑΝΤΙΣΤΑΣΕΩΣ'
        -- strop Λ. (avenue)
        WHEN road_name = 'Λ. ΑΘΗΝΩΝ' THEN 'ΑΘΗΝΩΝ'
        WHEN road_name = 'Λ. ΑΘΗΝΩΝ (ΠΑΡΑΛΛΗΛΟΣ)' THEN 'ΑΘΗΝΩΝ (ΠΑΡΑΛΛΗΛΟΣ)'
        WHEN road_name = 'Λ. ΑΛΕΞΑΝΔΡΑΣ' THEN 'ΑΛΕΞΑΝΔΡΑΣ'
        WHEN road_name = 'Λ. ΑΜΑΛΙΑΣ' THEN 'ΑΜΑΛΙΑΣ'
        WHEN road_name = 'Λ. ΒΟΥΛΙΑΓΜΕΝΗΣ' THEN 'ΒΟΥΛΙΑΓΜΕΝΗΣ'
        WHEN road_name = 'Λ. ΔΗΜΟΚΡΑΤΙΑΣ' THEN 'ΔΗΜΟΚΡΑΤΙΑΣ'
        WHEN road_name = 'Λ. ΚΑΡΑΜΑΝΛΗ ΚΩΝ.' THEN 'ΚΑΡΑΜΑΝΛΗ ΚΩΝ.'
        WHEN road_name = 'Λ. ΚΗΦΙΣΙΑΣ' THEN 'ΚΗΦΙΣΙΑΣ'
        WHEN road_name = 'Λ. ΚΗΦΙΣΟΥ' THEN 'ΚΗΦΙΣΟΥ'
        WHEN road_name = 'Λ. ΚΩΝΣΤΑΝΤΙΝΟΥΠΟΛΕΩΣ' THEN 'ΚΩΝΣΤΑΝΤΙΝΟΥΠΟΛΕΩΣ'
        WHEN road_name = 'Λ. ΜΕΣΟΓΕΙΩΝ' THEN 'ΜΕΣΟΓΕΙΩΝ'
        WHEN road_name = 'Λ. ΟΜΟΡΦΟΚΚΛΗΣΙΑΣ/ΒΕΪΚΟΥ' THEN 'ΟΜΟΡΦΟΚΚΛΗΣΙΑΣ/ΒΕΪΚΟΥ'
        WHEN road_name = 'Λ. ΣΥΓΓΡΟΥ' THEN 'ΣΥΓΓΡΟΥ'
        ELSE road_name 
    END AS road_name,
    road_info,
    ingested_at
from {{ ref("stg_traffic") }}

-- More robost deduplication in case the same device_id reports 
-- different roads at different times. It keeps the newest one.
qualify row_number() over (
    partition by device_id
    order by ingested_at desc
) = 1