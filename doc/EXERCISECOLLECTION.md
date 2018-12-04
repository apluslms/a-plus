ExerciseCollection
==================

ExerciseCollection is an exercisetype that can be used to define e.g. prerequisites
to other courses.
It collects points from student's submissions to specified course-instance and category.
Points can be rescaled to provide points like a any exercise.
The exercisepage provides links to each exercise in the category.


Grader-configuration file must contain following fields:

* **collection_category**
    
    Specifies the name of the target category.
    
* **collection_course** OR **collection_url**
    
    Specifies the course instance where the category is searched from.
    
    **collection_url** begin with the A+ service's BASE_URL.
    
    **collection_course** must be in format \<course\>;\<instance\>

Other requirements and restrictions:

* Group sizes and submissions are limited to 1.
* Target category can't be the same as the ExerciseCollection's