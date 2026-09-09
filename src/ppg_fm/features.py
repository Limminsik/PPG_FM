"""1단계 특징 이름 정의 — 모든 노트북이 여기서 가져다 쓴다.

박동 단위 23개 → 환자 단위 43개(중앙값 20 + 박동간 IQR 20 + 검출률 3).
"""

# 박동 단위 특징 — 계열별
TIMING = ["IBI", "CT", "LVET", "CT_over_LVET", "CT_over_IBI", "LVET_over_IBI",
          "dT", "W25", "W50", "W75", "W50_over_IBI"]                 # 11
AMP_RATIO = ["RI", "notch_rel_height", "IPA"]                        # 3
DERIV1 = ["max_slope_norm", "t_max_slope_rel"]                       # 2
APG = ["b_over_a", "c_over_a", "d_over_a", "e_over_a", "aging_index"]  # 5
FLAGS = ["notch_found", "apg_found"]                                 # 2

BEAT = TIMING + AMP_RATIO + DERIV1 + APG + FLAGS                     # 23

# 환자 요약에 들어가는 형태학 특징 (IBI는 HR로 바뀌므로 제외)
MORPH = [f for f in TIMING if f != "IBI"] + AMP_RATIO + DERIV1 + APG  # 20
IQR = [f + "_iqr" for f in MORPH]                                    # 20
RATE = ["cd_rate", "ri_rate", "lvet_rate"]                           # 3

PATIENT = MORPH + IQR + RATE                                         # 43

FAMILY = {
    "타이밍": TIMING, "정규화 진폭비": AMP_RATIO, "1차 미분": DERIV1,
    "2차 미분(APG)": APG, "검출 플래그": FLAGS,
}

# 환자 단위 43개의 계열 구분 — Figure 2의 행 묶음
PATIENT_FAMILY = [
    ("Timing", [f for f in TIMING if f != "IBI"]),      # 10
    ("Amplitude ratio", AMP_RATIO),                      # 3
    ("Derivatives", DERIV1 + APG),                       # 7
    ("Beat-to-beat IQR", IQR),                           # 20
    ("Detection rate", RATE),                            # 3
]
assert sum(len(v) for _, v in PATIENT_FAMILY) == 43

assert len(BEAT) == 23 and len(PATIENT) == 43
