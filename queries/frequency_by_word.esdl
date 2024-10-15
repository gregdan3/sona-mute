with
  F := (
    select Frequency {text}
    filter .length = 1 and .is_word
  ),
  groups := (
    group F {text, hits}
    using text := .text
    by text
  )
  select groups {
    word := .key.text,
    total := sum(.elements.hits)
  } order by .total desc;

