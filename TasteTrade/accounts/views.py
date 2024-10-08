
from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import authenticate, login
from django.http import HttpRequest, HttpResponse
from .forms import LoginForm
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import UserForm, ProfileUpdateForm, UserUpdateForm
from .models import Profile
from .forms import UserForm
from django.contrib import messages
from django.conf import settings
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required, user_passes_test
from products.models import Product
from orders.models import Order
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
import logging
from django.shortcuts import render
from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy

def signup_Bus(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()

                # Handle image upload
                image = request.FILES.get('image', None)

                profile = Profile.objects.create(
                    user=user, 
                    name=user.username, 
                    user_type='bus',
                    image=image ,
                    phone_number=request.POST['phone_number']
                      # Assign the image if available, otherwise None
                )
                logging.info(f"Profile created for user {user.username} with ID {profile.id}")
                return redirect('login_view')
            except Exception as e:
                logging.error(f"Error creating profile for user {user.username}: {str(e)}")
                messages.error(request, "There was an error creating your profile. Please try again.")
        else:
            logging.warning(f"Form is not valid. Errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserForm()
    return render(request, 'accounts/signup_Bus.html', {'form': form})


# views.py
def signup_Sup(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                user.save()
                profile_data = {
                    'user': user,
                    'name': request.POST['name'],
                    'phone_number': request.POST['phone_number'],
                    'image': request.FILES.get('image'),
                    'cr_file': request.FILES.get('cr'),
                    'bank_account_file': request.FILES.get('bank_account'),
                    'iban': request.POST['iban'],
                    'user_type': 'sup',
                }
                Profile.objects.create(**profile_data)
                logging.info(f"Profile created for user {user.username}")
                return redirect('login_view')
            except Exception as e:
                logging.error(f"Error creating profile for user {user.username}: {str(e)}")
                messages.error(request, "There was an error creating your profile. Please try again.")
        else:
            logging.warning(f"Form is not valid. Errors: {form.errors}")
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserForm()
    return render(request, 'accounts/signup_Sup.html', {'form': form})




def login_view(request: HttpRequest):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                return redirect('home')
                
            else:
                messages.error(request, "Invalid username or password. Please try again.", extra_tags="alert-danger")
    else:
        form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})





from django.shortcuts import render, get_object_or_404
from .models import Profile
from django.templatetags.static import static

from django.db.models import Avg
from orders.models import Review

def profile_view(request, profile_id):
    profile = get_object_or_404(Profile, id=profile_id)
    
    # Determine the image URL
    if profile.image:
        image_url = profile.image.url
    else:
        image_url = static('images/logo.png')

    # Determine if the "Statistics" button should be shown
    show_statistics_button = profile.user.profile.user_type == 'sup'
    
    # Calculate average rating
    reviews = Review.objects.filter(supplier_name=profile.user.profile.name)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    return render(request, 'accounts/profile.html', {
        'profile': profile,
        'image_url': image_url,
        'show_statistics_button': show_statistics_button,
        'avg_rating': avg_rating
    })






def signup_pop(request):
    return render(request, 'accounts/signup_options.html')

def forget_pop(request):
    return render(request, 'accounts/forget_pop.html')

def logout_pop(request):
    return render(request, 'accounts/logout_pop.html')



# myapp/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserUpdateForm, ProfileUpdateForm
from django.contrib.auth import logout


@login_required
def update_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save(commit=False)
            password = user_form.cleaned_data.get('password')

            if password:
                user.set_password(password)
                user.save()  # Save user first to ensure password change
                # Log the user out to force re-authentication after password change
                logout(request)
                messages.success(request, 'Your password has been changed. Please log in again.')
                return redirect('login')
            else:
                user.save()  # Save user if no password change

            profile_form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile_view', profile_id=request.user.profile.id)  # Ensure 'profile_view' and 'profile_id' are correctly configured

    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    return render(request, 'accounts/edit_profile.html', context)

@login_required
def supplier_statistics(request: HttpRequest):
    supplier = request.user

    # Filter only completed orders for the supplier
    completed_orders = Order.objects.filter(product__supplier=supplier, status='completed')

    # Filter completed orders for price income data
    price_income_data = (
        completed_orders
        .annotate(order_date=TruncDate('created_at'))
        .values('order_date')
        .annotate(total_income=Sum('total_price'))
        .order_by('order_date')
    )

    # Group by product to get quantity per product for completed orders
    orders_quantity_data = (
        completed_orders
        .values('product__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('product__name')
    )

    # Calculate total sales for completed orders
    total_sales = completed_orders.aggregate(total_sales=Sum('total_price'))['total_sales']

    # Get top products by sales quantity for completed orders
    top_products = (
        completed_orders
        .values('product__name')
        .annotate(total_quantity=Sum('quantity'))
        .order_by('-total_quantity')[:5]
    )

    # Get top customers for completed orders
    top_customers = (
        completed_orders
        .values('user__profile__name')
        .annotate(total_spending=Sum('total_price'))
        .order_by('-total_spending')[:5]
    )

    context = {
        'price_income_data': price_income_data,
        'orders_quantity_data': orders_quantity_data,
        'total_sales': total_sales,
        'top_products': top_products,
        'top_customers': top_customers,
    }

    return render(request, 'accounts/statics.html', context)



@login_required
def order_list_for_pdf(request: HttpRequest):
    user_profile = Profile.objects.get(user=request.user)
    user_type = user_profile.user_type

    # Get the selected status from the request
    selected_status = request.GET.get('status', '')

    if user_type == 'sup':
        # Get the products that belong to the supplier
        supplier_products = Product.objects.filter(supplier=request.user)
        # Filter orders based on these products
        orders = Order.objects.filter(product__in=supplier_products, status='completed')
    else:
        # If the user is a business owner, show their own completed orders
        orders = Order.objects.filter(user=request.user, status='completed')

    # Apply additional status filter if one is selected
    if selected_status:
        orders = orders.filter(status=selected_status)

    context = {
        'orders': orders,
        'user_type': user_type,
        'selected_status': selected_status,
    }
    return render(request, 'accounts/pdf_contract.html', context)


from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .forms import PasswordResetRequestForm
import random
import string

def password_reset_request(request):
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            try:
                user = User.objects.get(email=email)
                
                # Generate a temporary password
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                
                # Update user's password in the database
                user.set_password(temp_password)
                user.save()
                
                # Optionally, you can store the temporary password in a session or other method to provide it to the user
                request.session['temp_password'] = temp_password
                
                return redirect('password_reset_done')  # Redirect to a confirmation page or login page
            except User.DoesNotExist:
                form.add_error('email', 'No user with this email address.')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'accounts/password_reset_request.html', {'form': form})
