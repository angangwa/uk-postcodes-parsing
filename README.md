# uk-postcodes-parsing

[![Test](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/test.yml/badge.svg)](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/test.yml)
[![Upload Python Package](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/python-publish.yml/badge.svg)](https://github.com/anirudhgangwal/ukpostcodes/actions/workflows/python-publish.yml)

A Python package to parse UK postcodes from text. Useful in applications such as OCR and IDP.

## Install

```bash
pip install uk-postcodes-parsing
```

## Capabilities

- Search and parse UK postcode from text/OCR results
  - Extract parts of the postcode: incode, outcode etc.
  - Fix common mistakes in UK postcode OCR


| Postcode | .outcode | .incode | .area | .district | .subDistrict | .sector | .unit |
|----------|----------|---------|-------|-----------|--------------|---------|-------|
| AA9A 9AA | AA9A     | 9AA     | AA    | AA9       | AA9A         | AA9A 9  | AA    |
| A9A 9AA  | A9A      | 9AA     | A     | A9        | A9A          | A9A 9   | AA    |
| A9 9AA   | A9       | 9AA     | A     | A9        | `None`       | A9 9    | AA    |
| A99 9AA  | A99      | 9AA     | A     | A99       | `None`       | A99 9   | AA    |
| AA9 9AA  | AA9      | 9AA     | AA    | AA9       | `None`       | AA9 9   | AA    |
| AA99 9AA | AA99     | 9AA     | AA    | AA99      | `None`       | AA99 9  | AA    |


- Utilities to validate postcode
- Updated to November 2024: Validate postcode against ~1.8M UK postcodes from the ONS Postcode Directory


## Usage

- Parsing text to get a list of postcodes.

```python
>>> from uk_postcodes_parsing import ukpostcode
>>> corpus = "this is a check to see if we can get post codes liek thia ec1r 1ub , and that e3 4ss. But also eh16 50y and ei412"
>>> postcodes = ukpostcode.parse_from_corpus(corpus)
INFO:uk-postcodes-parsing:Found 2 postcodes in corpus
>>> postcodes
[Postcode(is_in_ons_postcode_directory=True, fix_distance=0, original='ec1r 1ub', postcode='EC1R 1UB', incode='1UB', outcode='EC1R', area='EC', district='EC1', sub_district='EC1R', sector='EC1R 1', unit='UB'),
 Postcode(is_in_ons_postcode_directory=True, fix_distance=0, original='e3 4ss', postcode='E3 4SS', incode='4SS', outcode='E3', area='E', district='E3', sub_district=None, sector='E3 4', unit='SS')]
```

- Optional auto-correct: Attempt correcting common mistakes in postcodes such as reading "O" and "0" and vice-versa.

```python
>>> from uk_postcodes_parsing import ukpostcode
>>> corpus = "this is a check to see if we can get post codes liek thia ec1r 1ub , and that e3 4ss. But also eh16 50y and ei412"
>>> postcodes = ukpostcode.parse_from_corpus(corpus, attempt_fix=True)
INFO:uk-postcodes-parsing:Found 3 postcodes in corpus
INFO:uk-postcodes-parsing:Postcode Fixed: 'eh16 50y' => 'EH16 5OY'
```

You can also do an undertermisitic postcode auto-correct where if there is more than one possible answer, all answers are returned.

```python
>>> postcodes = ukpostcode.parse_from_corpus("OOO 4SS",
                             attempt_fix=True,
                             try_all_fix_options=True
                             )
>> postcodes # "O00 4SS", "OO0 4SS", and "O0O 4SS"
[Postcode(is_in_ons_postcode_directory=False, fix_distance=-2, original='OOO 4SS', postcode='O00 4SS', incode='4SS', outcode='O00', area='O', district='O00', sub_district=None, sector='O00 4', unit='SS'),
 Postcode(is_in_ons_postcode_directory=False, fix_distance=-1, original='OOO 4SS', postcode='OO0 4SS', incode='4SS', outcode='OO0', area='OO', district='OO0', sub_district=None, sector='OO0 4', unit='SS'),
 Postcode(is_in_ons_postcode_directory=False, fix_distance=-1, original='OOO 4SS', postcode='O0O 4SS', incode='4SS', outcode='O0O', area='O', district='O0', sub_district='O0O', sector='O0O 4', unit='SS')]
```

- Parsing

```python
>>> from uk_postcodes_parsing import ukpostcode
>>> ukpostcode.parse("EC1r 1ub")
Postcode(is_in_ons_postcode_directory=True, fix_distance=0, original='EC1r 1ub', postcode='EC1R 1UB', incode='1UB', outcode='EC1R', area='EC', district='EC1', sub_district='EC1R', sector='EC1R 1', unit='UB')
```

```python
>>> ukpostcode.parse("EH16 50Y")
INFO:uk-postcodes-parsing:Postcode Fixed: 'EH16 50Y' => 'EH16 5OY'
Postcode(is_in_ons_postcode_directory=False, fix_distance=-1, original='EH16 50Y', postcode='EH16 5OY', incode='5OY', outcode='EH16', area='EH', district='EH16', sub_district=None, sector='EH16 5', unit='OY')
```

```python
>>> ukpostcode.parse("EH16 50Y", attempt_fix=False) # Don't attempt fixes during parsing
ERROR:uk-postcodes-parsing:Failed to parse postcode
>>> ukpostcode.parse("0W1")
ERROR:uk-postcodes-parsing:Unable to fix postcode
ERROR:uk-postcodes-parsing:Failed to parse postcode
```

- Validity check

```python
>>> from uk_postcodes_parsing import postcode_utils
>>> postcode_utils.is_valid("0W1 0AA")
False
>>> postcode_utils.is_valid("OW1 0AA")
True
```

- Fixing

```python
>>> from uk_postcodes_parsing.fix import fix
>>> fix("0W1 OAA")
'OW1 0AA'
```

- Validate against ONS Postcode directory (1.7M+ UK postcode upto Nov 2022)

```python
>>> ukpostcode.is_in_ons_postcode_directory("EC1R 1UB")
True
>>> ukpostcode.is_in_ons_postcode_directory("ec1r 1ub") # Expects normalised format (caps + space)
False
```


# Postcode class definition

```python
@dataclass(order=True)
class Postcode:
    # Calculate post initialization
    is_in_ons_postcode_directory: bool = field(init=False)
    fix_distance: int = field(init=False)
    # raw text
    original: str
    # The rest of the fields are parsed from the postcode using regex
    postcode: str
    incode: str
    outcode: str
    area: str
    district: str
    sub_district: Union[str, None]
    sector: str
    unit: str

```

- 2 fileds calculated after init of class
  - `is_in_ons_postcode_directory`: Checked against the [ONS Postcode Directory](https://geoportal.statistics.gov.uk/datasets/489c152010a3425f80a71dc3663f73e1/about)
  - `fix_distance`: A measure of number of characters changed from raw text. Each character fix adds a -1 (negative one) to this field.
    - E.g. `SW1A OAA` => `SW1A 0AA` has fix_distance=-1. Where as, `SWIA OAA` => `SW1A 0AA` has fix_distance=-2.
  - These fields are particularly helpful when using `parse_from_corpus` with `attempt_fix=True` which might return false positives. They can be used as proxy for confidence on which parsed postcodes are correct.
    - E.g. If you parse `"send the parcel back to one of the following postcodes: EC1R 1UB or EH16 5AY.` with `attempt_fix`:

      ```python
      >>> corpus = "send the parcel back to one of the following postcodes: ECIR 1UB or EH16 5AY"
      >>> postcodes = ukpostcode.parse_from_corpus(corpus, attempt_fix=True)
      INFO:uk-postcodes-parsing:Found 4 postcodes in corpus
      INFO:uk-postcodes-parsing:Postcode Fixed: 'to one' => 'T0 0NE'
      INFO:uk-postcodes-parsing:Postcode Fixed: 'llowing' => 'LL0W 1NG'
      INFO:uk-postcodes-parsing:Postcode Fixed: 'ecir 1ub' => 'EC1R 1UB'
      >>> postcodes # you get false positives
      [Postcode(is_in_ons_postcode_directory=False, fix_distance=-2, original='to one', postcode='T0 0NE', incode='0NE', outcode='T0', area='T', district='T0', sub_district=None, sector='T0 0', unit='NE'),
      Postcode(is_in_ons_postcode_directory=False, fix_distance=-2, original='llowing', postcode='LL0W 1NG', incode='1NG', outcode='LL0W', area='LL', district='LL0', sub_district='LL0W', sector='LL0W 1', unit='NG'),
      Postcode(is_in_ons_postcode_directory=True, fix_distance=-1, original='ecir 1ub', postcode='EC1R 1UB', incode='1UB', outcode='EC1R', area='EC', district='EC1', sub_district='EC1R', sector='EC1R 1', unit='UB'),
      Postcode(is_in_ons_postcode_directory=True, fix_distance=0, original='eh16 5ay', postcode='EH16 5AY', incode='5AY', outcode='EH16', area='EH', district='EH16', sub_district=None, sector='EH16 5', unit='AY')]
      ```

      You can sort a list of postcodes and chose the first n as needed:
      ```python
      >>> sorted(postcodes, reverse=True)
      [Postcode(is_in_ons_postcode_directory=True, fix_distance=0, original='eh16 5ay', postcode='EH16 5AY', incode='5AY', outcode='EH16', area='EH', district='EH16', sub_district=None, sector='EH16 5', unit='AY'),
      Postcode(is_in_ons_postcode_directory=True, fix_distance=-1, original='ecir 1ub', postcode='EC1R 1UB', incode='1UB', outcode='EC1R', area='EC', district='EC1', sub_district='EC1R', sector='EC1R 1', unit='UB'),
      Postcode(is_in_ons_postcode_directory=False, fix_distance=-2, original='to one', postcode='T0 0NE', incode='0NE', outcode='T0', area='T', district='T0', sub_district=None, sector='T0 0', unit='NE'),
      Postcode(is_in_ons_postcode_directory=False, fix_distance=-2, original='llowing', postcode='LL0W 1NG', incode='1NG', outcode='LL0W', area='LL', district='LL0', sub_district='LL0W', sector='LL0W 1', unit='NG')]
      ```
      Or:
      ```python
      >>> list(filter(lambda postcode: postcode.is_in_ons_postcode_directory, postcodes))
      [Postcode(is_in_ons_postcode_directory=True, fix_distance=-1, original='ecir 1ub', postcode='EC1R 1UB', incode='1UB', outcode='EC1R', area='EC', district='EC1', sub_district='EC1R', sector='EC1R 1', unit='UB'),
      Postcode(is_in_ons_postcode_directory=True, fix_distance=0, original='eh16 5ay', postcode='EH16 5AY', incode='5AY', outcode='EH16', area='EH', district='EH16', sub_district=None, sector='EH16 5', unit='AY')]
      ```


- `raw_text`: To keep track of the original string without formatting changes and auto-fixes.
- 8 fileds are parsed using regex

# Testing

```bash
pytest tests/
```

# ONSPD Data Processing Pipeline

This library includes tools to process ONS Postcode Directory (ONSPD) data into comprehensive databases with 25+ metadata fields per postcode. See the [ONSPD Usage Guide](docs/ONSPD_USAGE_GUIDE.md) and [ONSPD Technical Guide](docs/ONSPD_TECHNICAL_GUIDE.md) for details.

```bash
# Quick example: Create searchable database from ONSPD data
cd onspd_tools
python postcode_database_builder.py /path/to/onspd/multi_csv --output ../postcodes.db --validate
```

## Similar work

This package started as a Python replica of the postcode.io JavaScript library: https://github.com/ideal-postcodes/postcode
