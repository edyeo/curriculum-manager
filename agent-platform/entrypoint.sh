#!/bin/sh
case "$AGENT" in
  curriculum-manager)
    exec uvicorn apps.curriculum_manager.main:app --host 0.0.0.0 --port ${PORT:-8001}
    ;;
  mental-model-manager)
    exec uvicorn apps.mental_model_manager.main:app --host 0.0.0.0 --port ${PORT:-8002}
    ;;
  researcher)
    exec uvicorn apps.researcher.main:app --host 0.0.0.0 --port ${PORT:-8003}
    ;;
  question-generator)
    exec uvicorn apps.question_generator.main:app --host 0.0.0.0 --port ${PORT:-8004}
    ;;
  gateway)
    exec uvicorn apps.gateway:app --host 0.0.0.0 --port ${PORT:-9000}
    ;;
  grader)
    exec uvicorn apps.grader.main:app --host 0.0.0.0 --port ${PORT:-8005}
    ;;
  virtual-student)
    exec uvicorn apps.virtual_student.main:app --host 0.0.0.0 --port ${PORT:-8006}
    ;;
  kg-refiner)
    exec uvicorn apps.kg_refiner.main:app --host 0.0.0.0 --port ${PORT:-8007}
    ;;
  *)
    echo "Unknown AGENT: $AGENT"
    exit 1
    ;;
esac
