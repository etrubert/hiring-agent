#!/bin/bash
# Run 10 resumes with delays to respect Gemini free tier rate limits

RESUMES=(
  "test_resumes/junior-dev-resumes/choenden-kyirong/Resume.pdf"
  "test_resumes/junior-dev-resumes/emily-dowdle/emily_dowdle_20160917.pdf"
  "test_resumes/junior-dev-resumes/faiq-raza/Resume.pdf"
  "test_resumes/junior-dev-resumes/john-cato/resume.pdf"
  "test_resumes/junior-dev-resumes/robert-oconnor/resume.pdf"
  "test_resumes/junior-dev-resumes/shawna-c-scott/TechnicalResume.pdf"
  "test_resumes/junior-dev-resumes/sofiya-semenova/resume-fall2016.pdf"
  "test_resumes/dev_resume_adam.pdf"
  "test_resumes/frontend_amila.pdf"
  "test_resumes/resume_marisa.pdf"
)

rm -f resume_evaluations.csv

for i in "${!RESUMES[@]}"; do
  echo ""
  echo "============================================"
  echo "Processing resume $((i+1))/10: ${RESUMES[$i]}"
  echo "============================================"
  python score.py "${RESUMES[$i]}" 2>&1

  if [ $i -lt 9 ]; then
    echo "Waiting 65s for rate limit..."
    sleep 65
  fi
done

echo ""
echo "============================================"
echo "DONE! Check resume_evaluations.csv"
echo "============================================"
