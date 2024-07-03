with
  F := (
    select Frequency {text}
    filter .length = 1 and .is_word
  ),
  groups := (
    group F {text, occurrences}
    using text := .text
    by text
  )
  select groups {
    word := .key.text,
    total := sum(.elements.occurrences)
  } order by .total desc;

