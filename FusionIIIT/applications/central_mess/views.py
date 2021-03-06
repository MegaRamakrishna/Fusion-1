from datetime import date, datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from threading import Thread
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.views.generic import View
from django.db.models import Count
from django.forms.models import model_to_dict
from django.db.models import Q
from django.contrib.auth.models import User
from .utils import render_to_pdf
from background_task import background
from applications.academic_information.models import Student
from applications.globals.models import ExtraInfo, HoldsDesignation, Designation
from .forms import MinuteForm
from .models import (Feedback, Menu, Menu_change_request, Mess_meeting,
                     Mess_minutes, Mess_reg, Messinfo, Monthly_bill,
                     Nonveg_data, Nonveg_menu, Payments, Rebate,
                     Special_request, Vacation_food, MessBillBase)
from .handlers import (add_nonveg_order, add_mess_feedback, add_vacation_food_request,
                       add_menu_change_request, handle_menu_change_response, handle_vacation_food_request,
                       add_mess_registration_time, add_leave_request, add_mess_meeting_invitation,
                       handle_rebate_response, add_special_food_request,
                       handle_special_request, add_bill_base_amount, add_mess_committee, generate_bill)

today_g = datetime.today()
year_g = today_g.year
tomorrow_g = today_g + timedelta(days=1)


def mess(request):
    user = request.user
    extrainfo = ExtraInfo.objects.get(user=user)
    current_date = date.today()
    holds_designations = HoldsDesignation.objects.filter(user=user)
    desig = holds_designations
    print(desig)
    form = MinuteForm()
    mess_reg = Mess_reg.objects.last()
    count1 = 0
    count2 = 0
    count3 = 0
    count4 = 0
    count5 = 0
    count6 = 0
    count7 = 0
    count8 = 0

    # remove ths part after database has been updated
    change_desig = Designation.objects.filter(name="mess_committee").count()
    if change_desig:
        change_design = Designation.objects.get(name="mess_committee")
        change_design.name = "mess_committee_mess1"
        change_desig2 = Designation.objects.get(name="mess_convener")
        change_desig2.name = "mess_convener_mess1"
        change_desig_obj1 = Designation(name="mess_committee_mess2", full_name="Mess Committee", type="administrative")
        change_desig_obj2 = Designation(name="mess_convener_mess2", full_name="Mess Convener", type="administrative")
        change_desig_obj1.add()
        change_desig_obj2.add()
    #end of remove part

    if extrainfo.user_type == 'student':
        student = Student.objects.get(id=extrainfo)
        vaca_obj = Vacation_food.objects.filter(student_id=student)
        feedback_obj = Feedback.objects.filter(student_id=student)
        data = Nonveg_data.objects.filter(student_id=student)
        monthly_bill = Monthly_bill.objects.filter(student_id=student)
        payments = Payments.objects.filter(student_id=student)
        rebates = Rebate.objects.filter(student_id=student)
        meeting = Mess_meeting.objects.all()
        minutes = Mess_minutes.objects.all()
        sprequest = Special_request.objects.filter(status='1')
        splrequest = Special_request.objects.filter(student_id=student).order_by('-app_date')
        feed = Feedback.objects.all()
        messinfo = Messinfo.objects.get(student_id=student)
        newmenu = Menu_change_request.objects.all()
        count = 0
        #variable y stores the menu items
        mess_optn = Messinfo.objects.get(student_id=student)
        y = Menu.objects.filter(mess_option=mess_optn.mess_option)
        x = Nonveg_menu.objects.all()

        for item in rebates:
            d1 = item.start_date
            d2 = item.end_date
            item.duration = abs((d2 - d1).days)+1
            item.save()

        for items in rebates:
            if items.leave_type == 'casual':
                count += item.duration

        for f in feed:
            mess_opt = Messinfo.objects.get(student_id=f.student_id)
            if f.feedback_type == 'Maintenance' and mess_opt.mess_option == 'mess1':
                count1 += 1

            elif f.feedback_type == 'Food' and mess_opt.mess_option == 'mess1':
                count2 += 1

            elif f.feedback_type == 'Cleanliness' and mess_opt.mess_option == 'mess1':
                count3 += 1

            elif f.feedback_type == 'Others' and mess_opt.mess_option == 'mess1':
                count4 += 1

        for f in feed:
            mess_opt = Messinfo.objects.get(student_id=f.student_id)
            if f.feedback_type == 'Maintenance' and mess_opt.mess_option == 'mess2':
                count5 += 1

            elif f.feedback_type == 'Food' and mess_opt.mess_option == 'mess2':
                count6 += 1

            elif f.feedback_type == 'Cleanliness' and mess_opt.mess_option == 'mess2':
                count7 += 1

            elif f.feedback_type == 'Others' and mess_opt.mess_option == 'mess2':
                count8 += 1

        context = {
                   'menu': y,
                   'messinfo': messinfo,
                   'newmenu': newmenu,
                   'monthly_bill': monthly_bill,
                   'payments': payments,
                   'nonveg': x,
                   'vaca': vaca_obj,
                   'info': extrainfo,
                   'feedback': feedback_obj,
                   'feed': feed,
                   'student': student,
                   'data': data,
                   'mess_reg': mess_reg,
                   'current_date': current_date,
                   'count': count,
                   'rebates': rebates,
                   'meeting': meeting,
                   'minutes': minutes,
                   'sprequest': sprequest,
                   'splrequest': splrequest,
                   'count1': count1,
                   'count2': count2,
                   'count3': count3,
                   'count4': count4,
                   'count5': count5,
                   'count6': count6,
                   'count7': count7,
                   'count8': count8,
                   'form': form,
                   'desig': desig
            }

        return render(request, "messModule/mess.html", context)

    elif extrainfo.user_type == 'staff':
        current_bill = MessBillBase.objects.latest('timestamp')
        nonveg_orders = Nonveg_data.objects.filter(order_date=today_g)\
            .values('dish__dish','order_interval').annotate(total=Count('dish'))
        print(nonveg_orders)
        # make info with diff name and then pass context
        newmenu = Menu_change_request.objects.all()
        vaca_all = Vacation_food.objects.all()
        # members_mess = HoldsDesignation.objects.filter(designation__name='mess_convener')
        members_mess = HoldsDesignation.objects.filter(Q(designation__name__contains='mess_convener')
                                                       | Q(designation__name__contains='mess_committee'))
        print(members_mess)
        y = Menu.objects.all()
        x = Nonveg_menu.objects.all()
        leave = Rebate.objects.filter(status='1')

        context = {
                   'bill_base': current_bill,
                   'today': today_g,
                   'nonveg_orders': nonveg_orders,
                   'members': members_mess,
                   'menu': y,
                   'newmenu': newmenu,
                   'vaca_all': vaca_all,
                   'info': extrainfo,
                   'leave': leave,
                   'current_date': current_date,
                   'mess_reg': mess_reg,
                   'desig': desig,
        }

        return render(request, "messModule/mess.html", context)

    elif extrainfo.user_type == 'faculty':
        meeting = Mess_meeting.objects.all()
        minutes = Mess_minutes.objects.all()
        feed = Feedback.objects.all()
        y = Menu.objects.all()

        for f in feed:
            mess_opt = Messinfo.objects.get(student_id=f.student_id)
            if f.feedback_type == 'Maintenance' and mess_opt.mess_option == 'mess1':
                count1 += 1

            elif f.feedback_type == 'Food' and mess_opt.mess_option == 'mess1':
                count2 += 1

            elif f.feedback_type == 'Cleanliness' and mess_opt.mess_option == 'mess1':
                count3 += 1

            elif f.feedback_type == 'Others' and mess_opt.mess_option == 'mess1':
                count4 += 1

        for f in feed:
            mess_opt = Messinfo.objects.get(student_id=f.student_id)
            if f.feedback_type == 'Maintenance' and mess_opt.mess_option == 'mess2':
                count5 += 1

            elif f.feedback_type == 'Food' and mess_opt.mess_option == 'mess2':
                count6 += 1

            elif f.feedback_type == 'Cleanliness' and mess_opt.mess_option == 'mess2':
                count7 += 1

            elif f.feedback_type == 'Others' and mess_opt.mess_option == 'mess2':
                count8 += 1
            context = {
                 'info': extrainfo,
                 'menu': y,
                 'meeting': meeting,
                 'minutes': minutes,
                 'count1': count1,
                 'count2': count2, 'count3': count3, 'feed': feed,
                 'count4': count4, 'form': form, 'count5': count5,
                 'count6': count6, 'count7': count7, 'count8': count8, 'desig': desig
            }
        return render(request, 'messModule/mess.html',
                     )


@login_required
@transaction.atomic
@csrf_exempt
def place_order(request):
    """
    This function is to place non-veg food orders
    :param request:
        user: Current user
        order_interval: Time of the day for which order is placed eg breakfast/lunch/dinner
    :variables:
        extra_info: Extra information about the current user. From model ExtraInfo
        student: Student information about the current user
        student_mess: Mess choices of the student
        dish_request: Predefined dish available
    :return:
    """
    user = request.user
    extra_info = ExtraInfo.objects.get(user=user)

    if extra_info.user_type == 'student':
        student = Student.objects.get(id=extra_info)
        student_mess = Messinfo.objects.get(student_id=student)

        if student_mess.mess_option == 'mess1':
            add_nonveg_order(request, student)
            return HttpResponseRedirect('/mess')
        elif student_mess.mess_option == 'mess2':
            messages.info(request,"You cannot apply for non veg food")
        else:
            return HttpResponse("you can't apply for this application sorry for the inconvenience")


@csrf_exempt
@login_required
@transaction.atomic
def submit_mess_feedback(request):
    """
    This function is to record the feedback submitted
    :param request:
        user: Current logged in user
    :variable:
         extra_info: Extra information of the user
    :return:
        data: to record success or any errors
    """
    user = request.user
    extra_info = ExtraInfo.objects.get(user=user)
    student = Student.objects.get(id=extra_info)
    if extra_info.user_type == 'student':
        data = add_mess_feedback(request, student)
        return JsonResponse(data)


@csrf_exempt
@login_required
@transaction.atomic
def mess_vacation_submit(request):
    """
    This function is to record vacation food requests
    :param request:
        user: Current user information
    :variables:
    :return:
        data: JsonResponse
    """
    user = request.user
    extra_info = ExtraInfo.objects.get(user=user)
    student = Student.objects.get(id=extra_info)
    if extra_info.user_type == 'student':
        data = add_vacation_food_request(request, student)
        return JsonResponse(data)


@login_required
@transaction.atomic
def submit_mess_menu(request):
    """
    This function is to record mess menu change requests by the  mess_committee
    :param request:
        user:Current user
    :return:
    """
    # TODO add ajax for this
    user = request.user
    holds_designations = HoldsDesignation.objects.filter(user=user)
    designation = holds_designations
    context = {}
    # A user may hold multiple designations

    data = add_menu_change_request(request)
    if data['status'] == 1:
        return HttpResponseRedirect("/mess")

    return render(request, 'messModule/mess.html', context)


@login_required
def menu_change_response(request):
    """
    This function is to respond to mess menu requests
    :param request:
        user: Current user
    :return:
    """
    user = request.user
    holds_designations = HoldsDesignation.objects.filter(user=user)
    designation = holds_designations
    for d in designation:
        if d.designation.name == 'mess_manager':
           data = handle_menu_change_response(request)
        return JsonResponse(data)


@login_required
def response_vacation_food(request, ap_id):
    """
    This function records the response to vacation food requests
    :param request:
        user: Current user
    :param ap_id:
    :variables:
        holds_designations: Designation of the current user
    :return:
    """
    user = request.user
    # extra_info = ExtraInfo.objects.get(user=user)
    holds_designations = HoldsDesignation.objects.filter(user=user)
    designation = holds_designations

    for d in designation:
        if d.designation.name == 'mess_manager':
            data = handle_vacation_food_request(request, ap_id)
    return HttpResponseRedirect("/mess")


@login_required
@transaction.atomic
def regsubmit(request):

    i = 0
    j = 0
    month_1 = ['January', 'February', 'March', 'April', 'May', 'June']
    month_2 = ['July', 'August', 'September', 'October', 'November', 'December']
    user = request.user
    extrainfo = ExtraInfo.objects.get(user=user)

    if extrainfo.user_type == 'student':
        student = Student.objects.get(id=extrainfo)
        mess = request.POST.get('mess_type')
        mess_info_inst = Messinfo.objects.get(student_id=student)
        mess_info_inst.mess_option = mess
        mess_info_inst.save()
        mess_reg = Mess_reg.objects.last()

        if Monthly_bill.objects.filter(student_id=student):
            return HttpResponseRedirect("/mess")

        else:

            if mess_reg.end_reg.strftime("%B") in month_1:
                while i<=5:
                    monthly_bill_obj = Monthly_bill(student_id=student, month=month_1[i])
                    monthly_bill_obj.save()
                    i = i+1

            else:
                while j<=5:
                    monthly_bill_obj = Monthly_bill(student_id=student, month=month_2[j])
                    monthly_bill_obj.save()
                    j = j+1

        return HttpResponseRedirect("/mess")

    else:
        return redirect('mess')


@login_required
@transaction.atomic
def start_mess_registration(request):
    """
       This function is to start mess registration
       @request:
           user: Current user
           designation: designation of current user to validate proper platform
    """
    #   TODO ajax convert add a section to see previous sessions as well as close a session
    user = request.user
    designation = HoldsDesignation.objects.filter(user=user)
    for d in designation:
        if d.designation.name == 'mess_manager':
            data = add_mess_registration_time(request)
            return HttpResponseRedirect("/mess")


@transaction.atomic
@csrf_exempt
def mess_leave_request(request):
    """
        This function is to record and validate leave requests
        @request:
            user: Current user
        @variables:
            student: Information od student submitting the request
    """
    user = request.user
    extra_info = ExtraInfo.objects.get(user=user)
    student = Student.objects.get(id=extra_info)
    data = add_leave_request(request, student)
    return JsonResponse(data)


@login_required
@transaction.atomic
def minutes(request):
    """
    To upload the minutes of the meeting
    :param request:
    :return:
    """
    if request.method == 'POST' and request.FILES:
        form = MinuteForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponse('success')
        else:
            return HttpResponse("not uploaded")


@csrf_exempt
@transaction.atomic
def invitation(request):
    """
       This function is to schedule a mess committee meeting
       @request:
       @variables:
    """
    # todo add ajax to this page as well
    data = add_mess_meeting_invitation(request)
    return HttpResponseRedirect("/mess")


@login_required
@transaction.atomic
@csrf_exempt
def rebate_response(request):
    """
       This function is to respond to rebate requests
       :param request: user: Current user
       @variables: designation : designation of the user
       @return:
            data: returns the status of the application
    """
    data = {
        'status': 1
    }
    user = request.user
    designation = HoldsDesignation.objects.filter(user=user)
    for d in designation:
        if d.designation.name == 'mess_manager':
            data = handle_rebate_response(request)
    return JsonResponse(data)


@login_required
@transaction.atomic
@csrf_exempt
def place_request(request):
    # This is for placing special food request
    """
        This function is to place special food requests ( used by students )
        @variables:
        user: Current user
        @return:
        data['status']: returns status of the application
    """
    user = request.user
    extra_info = ExtraInfo.objects.get(user=user)
    if extra_info.user_type == 'student':
        extra_info = ExtraInfo.objects.get(user=user)
        student = Student.objects.get(id=extra_info)
        data = add_special_food_request(request, student)
        return JsonResponse(data)


@login_required
@transaction.atomic
@csrf_exempt
def special_request_response(request):
    """
       This function is to respond to special request for food submitted by students
       data: message regarding the request
    """
    data = handle_special_request(request)
    return JsonResponse(data)


@login_required
@transaction.atomic
@csrf_exempt
def update_cost(request):
    """
    This function is to update the base cost of the monthly central mess bill
    :param request:
    :return:
    """
    user = request.user
    # extrainfo = ExtraInfo.objects.get(user=user)
    data = add_bill_base_amount(request)
    return JsonResponse(data)


def generate_mess_bill(request):
    """
        This function is to generate the bill of the students
        @variables:
        user: stores current user information
        nonveg_data : stores records of non-veg ordered by a student
        year_now: current year
        month_now: current month
        amount_m: monhly base amount
        students: information of all students
        mess_info: Mess Information, mainly choice of mess
        rebates: Rebate records of students
        """
    # todo generate proper logic for generate_mess_bill
    user = request.user
    t1 = Thread(target=generate_bill, args=())
    t1.setDaemon(True)
    t1.start()
    # int = generate_bill()
    data ={
        'status': 1
    }
    return JsonResponse(data)

    
class MenuPDF(View):

    def post(self, request, *args, **kwargs):
        user = request.user
        extra_info = ExtraInfo.objects.get(user=user)
        y = Menu.objects.all()

        if extra_info.user_type=='student':
            student = Student.objects.get(id=extra_info)
            mess_info = Messinfo.objects.get(student_id=student)
            mess_option = mess_info.mess_option
            context = {
                'menu': y,
                'mess_option': mess_option
            }
            if mess_option=='mess2':
                return render_to_pdf('messModule/menudownloadable2.html', context)
            else:
                return render_to_pdf('messModule/menudownloadable1.html', context)
        else:
            context = {
                'menu': y,
                'mess_option': 'mess2'
            }
            return render_to_pdf('messModule/menudownloadable2.html', context)
        # return HttpResponse(pdf, content_type='application/pdf')


class MenuPDF1(View):
    # This function is to generate the menu in pdf format (downloadable) for mess 1
    def post(self, request, *args, **kwargs):
        user = request.user
        # extrainfo = ExtraInfo.objects.get(user=user)
        y = Menu.objects.all()
        context = {
            'menu': y,
            'mess_option': 'mess1'
        }
        return render_to_pdf('messModule/menudownloadable1.html', context)


def menu_change_request(request):
    newmenu = Menu_change_request.objects.filter(status=2)
    data = model_to_dict(newmenu)
    return JsonResponse(data)


def submit_mess_committee(request):
    roll_number = request.POST['rollnumber']
    data = add_mess_committee(request, roll_number)
    return JsonResponse(data)


def remove_mess_committee(request):
    member_id = request.POST['member_id']
    data_m = member_id.split("-")
    roll_number = data_m[1]
    if data_m[0] == 'mess_committee_mess1':
        designation = Designation.objects.get(name='mess_committee_mess1')
    elif data_m[0] == 'mess_convener_mess1':
        designation = Designation.objects.get(name='mess_convener_mess1')
    elif data_m[0] == 'mess_committee_mess2':
        designation = Designation.objects.get(name='mess_committee_mess2')
    else:
        designation = Designation.objects.get(name='mess_convener_mess2')
    remove_object = HoldsDesignation.objects.get(Q(user__username=roll_number) & Q(designation=designation))
    remove_object.delete()
    data = {
        'status': 1,
        'message': 'Successfully removed '
    }
    return JsonResponse(data)


def get_leave_data(request):
    leave_data = Rebate.objects.filter(Q(start_date__lte=today_g)&Q(end_date__gte=today_g)).count()
    leave_data_t = Rebate.objects.filter(Q(start_date__lte=tomorrow_g)&Q(end_date__gte=tomorrow_g)).count()
    data = {
        'status': 1,
        'message': 'HI I AM WORKING',
        'today': today_g.date(),
        'tomorrow': tomorrow_g.date(),
        'counttoday': leave_data,
        'counttomorrow':leave_data_t
    }
    return JsonResponse(data)


def accept_vacation_leaves(request):
    start_date_leave = request.GET['start_date']
    end_date_leave = request.GET['end_date']
    leave_data = Rebate.objects.filter(Q(start_date__gte=start_date_leave)
                                       &Q(end_date__lte=end_date_leave)
                                       &Q(leave_type="vacation")
                                       &Q(status='1'))
    if leave_data:
        for item in leave_data:
            item.status = '2'
            item.save()

    data = {
        'status': 1,
        'display': 'Vacation Leaves Successfully Accepted'
    }
    return JsonResponse(data)


def select_mess_convener(request):
    member_id = request.POST['member_id_add']
    data_m = member_id.split("-")
    roll_number = data_m[1]
    if data_m[0] == 'mess_committee_mess1':
        designation = Designation.objects.get(name='mess_committee_mess1')
        new_designation = Designation.objects.get(name='mess_convener_mess1')
        # One mess can have only one mess convener
        existing_check = HoldsDesignation.objects.filter(designation=new_designation)
        if existing_check.count():
            data = {
                'status': 1,
                'message': 'Mess Convener already exists for Mess 1 ! \nRemove the existing convener to add new one'
            }
            return JsonResponse(data)
        else:
            modify_object = HoldsDesignation.objects.get(Q(user__username=roll_number) & Q(designation=designation))
            modify_object.designation = new_designation
            modify_object.save()
    else:
        designation = Designation.objects.get(name='mess_committee_mess2')
        new_designation = Designation.objects.get(name='mess_convener_mess2')
        existing_check = HoldsDesignation.objects.filter(designation=new_designation)
        if existing_check.count():
            data = {
                'status': 1,
                'message': 'Mess Convener already exists for Mess 2 ! \n Remove the existing convener to add new one'
            }
            return JsonResponse(data)
        else:
            modify_object = HoldsDesignation.objects.get(Q(user__username=roll_number) & Q(designation=designation))
            modify_object.designation = new_designation
            modify_object.save()

    data = {
        'status': 1,
        'message': 'Successfully added as mess convener ! '
    }
    return JsonResponse(data)
