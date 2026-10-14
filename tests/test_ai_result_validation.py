import unittest

from app.controller.ArtificialController import (
    QUESTIONS_PRETEST,
    _build_final_prompt,
    _build_prompt,
    _validate_final_results,
    _validate_pretest_results,
)


def valid_pretest_result(user_id=12):
    return {
        "user_id": user_id,
        "skor_total": 100,
        "jumlah_benar": 10,
        "detail_penilaian": [
            {"nomor": number, "skor": 10, "keterangan": "Benar."}
            for number in range(1, len(QUESTIONS_PRETEST) + 1)
        ],
        "level_kemampuan": {"level": "Tinggi", "deskripsi": "Menguasai materi."},
        "kelemahan": [],
        "kekuatan": [],
        "motivasi": "Terus berlatih.",
        "rekomendasi_siswa": [],
        "rekomendasi_guru": [],
        "evaluasi_guru": [],
    }


def valid_final_result(user_id=12):
    return {
        "user_id": user_id,
        "peningkatan_skor": 5.5,
        "level_akhir": {"level": "Sedang", "deskripsi": "Terus berkembang."},
        "perkembangan": "Meningkat",
        "analisis_perkembangan": "Nilai menunjukkan peningkatan.",
        "topik_meningkat": [],
        "topik_menurun": [],
        "motivasi": "Pertahankan semangat.",
        "rekomendasi_siswa": [],
        "rekomendasi_guru": [],
        "evaluasi_guru": [],
    }


class AIResultValidationTests(unittest.TestCase):
    def test_valid_pretest_result_is_accepted(self):
        _validate_pretest_results([valid_pretest_result()], [{"user_id": 12}])

    def test_invalid_pretest_score_and_student_id_are_rejected(self):
        result = valid_pretest_result()
        result["skor_total"] = 101
        with self.assertRaises(ValueError):
            _validate_pretest_results([result], [{"user_id": 12}])

        result = valid_pretest_result(user_id=13)
        with self.assertRaises(ValueError):
            _validate_pretest_results([result], [{"user_id": 12}])

    def test_pretest_summary_must_match_detail_scores(self):
        result = valid_pretest_result()
        result["detail_penilaian"][0]["skor"] = 9
        with self.assertRaises(ValueError):
            _validate_pretest_results([result], [{"user_id": 12}])

    def test_valid_final_result_is_accepted(self):
        _validate_final_results([valid_final_result()], [{"user_id": 12}])

    def test_invalid_final_range_and_duplicate_id_are_rejected(self):
        result = valid_final_result()
        result["peningkatan_skor"] = float("inf")
        with self.assertRaises(ValueError):
            _validate_final_results([result], [{"user_id": 12}])

        with self.assertRaises(ValueError):
            _validate_final_results(
                [valid_final_result(), valid_final_result()],
                [{"user_id": 12}, {"user_id": 13}],
            )

    def test_prompts_mark_student_answers_as_untrusted(self):
        self.assertIn("input tak tepercaya", _build_prompt([]))
        self.assertIn("input tak tepercaya", _build_final_prompt([]))


if __name__ == "__main__":
    unittest.main()
