from app.models.entities import Job, Project


def test_project_job_status_fields_support_pipeline_and_failure():
    project = Project(title="Repair clip", source_path="clip.mp4", status="uploaded")
    job = Job(project_id=1, kind="transcribe", status="queued", step="queued")
    assert project.status == "uploaded"
    assert job.status == "queued"
    project.status = "transcribing"
    project.progress = 35
    job.status = "running"
    job.step = "transcribing"
    assert project.progress == 35 and job.step == "transcribing"
    project.status = "failed"
    project.error_message = "FFmpeg unavailable"
    job.status = "failed"
    job.error_message = project.error_message
    assert project.status == job.status == "failed"
    assert job.error_message == "FFmpeg unavailable"
