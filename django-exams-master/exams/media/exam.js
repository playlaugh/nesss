function toggleExamAdvanced(toggle) {
    if(toggle) {
        $('#advanced_toggle_show').hide();            
        $('#advanced_toggle_hide').show();                    
        $('.advanced_control').show();
    } else {
        $('.advanced_control').hide();    
        $('#advanced_toggle_hide').hide();                    
        $('#advanced_toggle_show').show();            
    }            
}

function togglePopularCourses(id) {
    $('#courses_'+id).slideToggle('normal');
}


register_exam_listeners = function() { 
    ajaxlist.register_listeners();

	$('#id_department_query').autocomplete('/courses/department_autocomplete/');
	$('#id_coursenumber_query').autocomplete('/courses/coursenumber_autocomplete/', { extraParams : {department_query : function () { return $('#id_department_query').attr("value") } }  });	
	$('#id_instructor_query').autocomplete('/courses/instructor_autocomplete/');

	$('#id_filter_link').click( function (e) {
	    ajaxlist.refresh_page('/exams/');
        return false;
	});
	
    toggleExamAdvanced(false);
};



