# -*- coding: utf-8 -*-
import logging
import datetime

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.db.models import Q, F
from django.contrib.auth.models import User
from django.conf import settings
from django.utils.timezone import utc

import decorators
from utils import http
from config import codes
from . import forms
from . import services
from . import models as tokensale_models

logger = logging.getLogger(__name__)

@login_required
def show_tokensale_index_view(request):
    return render(request, "tokensale/index.html", locals()) 

@login_required
def show_join_tokensale_view(request):
    instance = tokensale_models.KYCInfo.objects.filter(user=request.user, phase_id=settings.CURRENT_FUND_PHASE).first()
    form = forms.KYCInfoForm(instance=instance)
    return render(request, "tokensale/submit.html", locals()) 

@login_required
@decorators.http_post_required
def post_kyc_information(request):
    try:
        # TODO twice submit tokensale info need check.
        form = forms.KYCInfoForm(request.POST, request.FILES)
        if not form.is_valid():
            return render(request, "tokensale/submit.html", locals())
        # check whether user is submit kyc info
        instance = tokensale_models.KYCInfo.objects.filter(user=request.user, phase_id=settings.CURRENT_FUND_PHASE).first()
        instance = form.save(commit=False)
        instance.phase_id = settings.CURRENT_FUND_PHASE
        instance.user = request.user
        instance.save()
        email = request.user.email
        services.send_kyc_confirm_email(email, request)
        return redirect('/tokensale/wait-audit/')
    except Exception, inst:
        logger.exception("fail to post kyc information:%s" % str(inst))
        return http.HttpResponseServerError()

@login_required
def show_wait_audit_view(request):
    return render(request, "tokensale/wait-audit.html", locals())

def verify_email_link(request):
    try:
        uuid = request.GET['uuid']
        verification = services.get_kyc_verification_by_uuid(uuid)
        if not verification:
            return http.HttpResponseRedirect('/tokensale/invalid-link/')
            #check link status
        verification_status = verification.status
        if verification_status != codes.StatusCode.AVAILABLE.value:
            return http.HttpResponseRedirect('/tokensale/invalid-link/')
        email = verification.email_address
        expire_time = verification.expire_time
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        # don't check whether the given link is expired
        #if now > expire_time:
            #return http.HttpResponseRedirect('/tokensale/invalid-link/')
        return http.HttpResponseRedirect('/tokensale/limit-address/?uuid=%s' %str(uuid))
    except Exception, inst:
        logger.exception('fail to verify email link: %s' % str(inst))
        return http.HttpResponseServerError()
        
    return render(request, "tokensale/wait-audit.html", locals())

def show_limit_and_address_view(request):
    uuid = request.GET['uuid']
    verification = services.get_kyc_verification_by_uuid(uuid)
    if not verification:
        return http.HttpResponseRedirect('/tokensale/invalid-link/')
        #check link status
    verification_status = verification.status
    if verification_status != codes.StatusCode.AVAILABLE.value:
        return http.HttpResponseRedirect('/tokensale/invalid-link/')
    email = verification.email_address
    user = User.objects.filter(email=email).first()
    if not user:
        return http.HttpResponseRedirect('/tokensale/invalid-link/')
    kycinfo = tokensale_models.KYCInfo.objects.filter(user=user).first()
    if not kycinfo:
        return http.HttpResponseRedirect('/tokensale/invalid-link/')
    form = forms.KYCAddressForm(instance=kycinfo)
    return render(request, "tokensale/limit-address.html", locals())

def show_invalid_link(request):
    return render(request, "tokensale/invalid-link.html", locals())