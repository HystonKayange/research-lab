# LM baselines v0.1 — validation results (provisional)

_Generated 2026-08-05T08:49:45.193024Z_

Test evaluation has **not** been run. Leaders below are **provisional**.

## architecture_matched × fixed_characters

Provisional validation leader: **unigram_8000** (mean BPC=1.4313127134139931)

| tokenizer | mean BPC | std | median | min | max | mean BPB | n |
|-----------|---------:|----:|-------:|----:|----:|---------:|--:|
| character | 1.4778541708704187 | 0.007046592563308197 | 1.4762954087385072 | 1.4717174719617532 | 1.485549631910996 | 1.4635405640274282 | 3 |
| bpe_8000 | 1.438936199882615 | 0.0018601234021981589 | 1.439966637183555 | 1.4367888941333573 | 1.4400530683309323 | 1.4249995291046476 | 3 |
| unigram_8000 | 1.4313127134139931 | 0.000617047968967632 | 1.4309637303326443 | 1.4309492399904677 | 1.432025169918867 | 1.4174498791418433 | 3 |

### Paired seed differences (BPC)

- **bpe_minus_character**: mean diff=-0.038917970987803883 (std=0.006891738007625412); pairs=[{'seed': 42, 'diff': -0.04549656358006371}, {'seed': 1337, 'diff': -0.03175083477819807}, {'seed': 2026, 'diff': -0.03950651460514987}]
- **unigram_minus_character**: mean diff=-0.04654145745642572 (std=0.007518401632195614); pairs=[{'seed': 42, 'diff': -0.05458590157835164}, {'seed': 1337, 'diff': -0.039692302042886096}, {'seed': 2026, 'diff': -0.04534616874803943}]
- **unigram_minus_bpe**: mean diff=-0.007623486468621839 (std=0.0016480124787177323); pairs=[{'seed': 42, 'diff': -0.009089337998287927}, {'seed': 1337, 'diff': -0.007941467264688029}, {'seed': 2026, 'diff': -0.005839654142889561}]

Provisional validation leader only; test evaluation still required.

## architecture_matched × fixed_updates

Provisional validation leader: **unigram_8000** (mean BPC=1.4433547294988347)

| tokenizer | mean BPC | std | median | min | max | mean BPB | n |
|-----------|---------:|----:|-------:|----:|----:|---------:|--:|
| character | 1.886783820467372 | 0.010983058166124363 | 1.8843258181818257 | 1.8772380253125969 | 1.8987876179076932 | 1.868509566933967 | 3 |
| bpe_8000 | 1.4567035028458353 | 0.0015833748310600108 | 1.4563571521032426 | 1.45532197350949 | 1.4584313829247735 | 1.4425947486551145 | 3 |
| unigram_8000 | 1.4433547294988347 | 0.0013617537187171512 | 1.4428717481894078 | 1.4423002957801767 | 1.4448921445269196 | 1.4293752634999335 | 3 |

### Paired seed differences (BPC)

- **bpe_minus_character**: mean diff=-0.4300803176215366 (std=0.012464385232177428); pairs=[{'seed': 42, 'diff': -0.4188066423878234}, {'seed': 1337, 'diff': -0.4279686660785831}, {'seed': 2026, 'diff': -0.44346564439820324}]
- **unigram_minus_character**: mean diff=-0.4434290909685372 (std=0.011045049164535303); pairs=[{'seed': 42, 'diff': -0.43493772953242016}, {'seed': 1337, 'diff': -0.43943367365490604}, {'seed': 2026, 'diff': -0.45591586971828546}]
- **unigram_minus_bpe**: mean diff=-0.01334877334700065 (std=0.0024593934316970963); pairs=[{'seed': 42, 'diff': -0.016131087144596767}, {'seed': 1337, 'diff': -0.01146500757632296}, {'seed': 2026, 'diff': -0.01245022532008222}]

Provisional validation leader only; test evaluation still required.

## parameter_matched × fixed_characters

Provisional validation leader: **unigram_8000** (mean BPC=1.4370611407962612)

| tokenizer | mean BPC | std | median | min | max | mean BPB | n |
|-----------|---------:|----:|-------:|----:|----:|---------:|--:|
| character | 1.4778541708704187 | 0.007046592563308197 | 1.4762954087385072 | 1.4717174719617532 | 1.485549631910996 | 1.4635405640274282 | 3 |
| bpe_8000 | 1.446280867650161 | 0.0015439476750195326 | 1.4464671984757287 | 1.4446522104461974 | 1.447723194028557 | 1.432273060836657 | 3 |
| unigram_8000 | 1.4370611407962612 | 0.000582143383736956 | 1.436836690240743 | 1.436624633552363 | 1.4377220985956776 | 1.423142630713103 | 3 |

### Paired seed differences (BPC)

- **bpe_minus_character**: mean diff=-0.03157330322025772 (std=0.008243980176616079); pairs=[{'seed': 42, 'diff': -0.04089742146479858}, {'seed': 1337, 'diff': -0.025250273486024488}, {'seed': 2026, 'diff': -0.028572214709950083}]
- **unigram_minus_character**: mean diff=-0.04079303007415761 (std=0.0065459289819271025); pairs=[{'seed': 42, 'diff': -0.047827533315318416}, {'seed': 1337, 'diff': -0.03488078172101017}, {'seed': 2026, 'diff': -0.03967077518614426}]
- **unigram_minus_bpe**: mean diff=-0.009219726853899898 (std=0.0021143668067548317); pairs=[{'seed': 42, 'diff': -0.006930111850519838}, {'seed': 1337, 'diff': -0.00963050823498568}, {'seed': 2026, 'diff': -0.011098560476194175}]

Provisional validation leader only; test evaluation still required.

## parameter_matched × fixed_updates

Provisional validation leader: **unigram_8000** (mean BPC=1.4793057103427036)

| tokenizer | mean BPC | std | median | min | max | mean BPB | n |
|-----------|---------:|----:|-------:|----:|----:|---------:|--:|
| character | 1.886783820467372 | 0.010983058166124363 | 1.8843258181818257 | 1.8772380253125969 | 1.8987876179076932 | 1.868509566933967 | 3 |
| bpe_8000 | 1.4987472218621383 | 0.0014937941702598716 | 1.4983353760942155 | 1.4975025557896113 | 1.5004037337025877 | 1.4842312574905492 | 3 |
| unigram_8000 | 1.4793057103427036 | 0.00202422592517248 | 1.4800099138122642 | 1.4770234366722568 | 1.4808837805435897 | 1.464978044761217 | 3 |

### Paired seed differences (BPC)

- **bpe_minus_character**: mean diff=-0.3880365986052337 (std=0.009491096349212618); pairs=[{'seed': 42, 'diff': -0.37973546952298554}, {'seed': 1337, 'diff': -0.38599044208761013}, {'seed': 2026, 'diff': -0.3983838842051055}]
- **unigram_minus_character**: mean diff=-0.40747811012466834 (std=0.012756256909778501); pairs=[{'seed': 42, 'diff': -0.39722811150033266}, {'seed': 1337, 'diff': -0.40344203763823594}, {'seed': 2026, 'diff': -0.42176418123543646}]
- **unigram_minus_bpe**: mean diff=-0.01944151151943463 (std=0.003411150052097059); pairs=[{'seed': 42, 'diff': -0.017492641977347123}, {'seed': 1337, 'diff': -0.01745159555062581}, {'seed': 2026, 'diff': -0.023380297030330954}]

Provisional validation leader only; test evaluation still required.

## Source-specific validation observations

- architecture_matched/fixed_characters: unigram_8000 performed better on both Bible and Wikipedia validation under this configuration (provisional; test evaluation is still required).
- architecture_matched/fixed_updates: unigram_8000 performed better on both Bible and Wikipedia validation under this configuration (provisional; test evaluation is still required).
- parameter_matched/fixed_characters: unigram_8000 performed better on both Bible and Wikipedia validation under this configuration (provisional; test evaluation is still required).
- parameter_matched/fixed_updates: unigram_8000 performed better on both Bible and Wikipedia validation under this configuration (provisional; test evaluation is still required).

### architecture_matched × fixed_characters

| tokenizer | combined BPC | bible BPC | wiki BPC |
|-----------|-------------:|----------:|---------:|
| character | 1.4778289154482367 | 1.30132784655937 | 1.9305286027109527 |
| bpe_8000 | 1.438908085388929 | 1.2466024603185104 | 1.9327047386109721 |
| unigram_8000 | 1.4312871152776012 | 1.237480302830338 | 1.9269344895706173 |

Leaders (provisional): combined=unigram_8000, bible=unigram_8000, wikipedia=unigram_8000.

### architecture_matched × fixed_updates

| tokenizer | combined BPC | bible BPC | wiki BPC |
|-----------|-------------:|----------:|---------:|
| character | 1.8867322066062695 | 1.6790692084013619 | 2.422706393972817 |
| bpe_8000 | 1.4566852886178503 | 1.270324835374033 | 1.9357664380854054 |
| unigram_8000 | 1.4433490713652228 | 1.2551260374976776 | 1.924531295678536 |

Leaders (provisional): combined=unigram_8000, bible=unigram_8000, wikipedia=unigram_8000.

### parameter_matched × fixed_characters

| tokenizer | combined BPC | bible BPC | wiki BPC |
|-----------|-------------:|----------:|---------:|
| character | 1.4778289154482367 | 1.30132784655937 | 1.9305286027109527 |
| bpe_8000 | 1.446256612109303 | 1.2558282279688975 | 1.9363249260416515 |
| unigram_8000 | 1.4370387747255533 | 1.2455074448929901 | 1.9276292885258186 |

Leaders (provisional): combined=unigram_8000, bible=unigram_8000, wikipedia=unigram_8000.

### parameter_matched × fixed_updates

| tokenizer | combined BPC | bible BPC | wiki BPC |
|-----------|-------------:|----------:|---------:|
| character | 1.8867322066062695 | 1.6790692084013619 | 2.422706393972817 |
| bpe_8000 | 1.4987158474084925 | 1.3110316014885677 | 1.9822121637276802 |
| unigram_8000 | 1.4792742221097754 | 1.2930440874473774 | 1.9566637203376862 |

Leaders (provisional): combined=unigram_8000, bible=unigram_8000, wikipedia=unigram_8000.

Language: these are validation-only observations. Do not claim statistical significance from three seeds alone. Test evaluation is still required.

Figures: `/home/cyai/projects/research/transformer-lab/data/reports/figures/lm_baselines_v0.1/final_validation`