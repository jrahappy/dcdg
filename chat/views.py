from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count, F
from django.core.paginator import Paginator
from django.utils import timezone
from .models import ChatRoom, ChatMessage, ChatNotification
from .forms import ChatRoomForm, ChatMessageForm


@login_required
def chat_list(request):
    """List all chat rooms for the current user"""
    if request.user.is_staff:
        # Get filter parameter
        filter_type = request.GET.get('filter', 'all')
        
        # Base queryset for staff
        chat_rooms = ChatRoom.objects.all()
        
        # Apply filters
        if filter_type == 'unassigned':
            chat_rooms = chat_rooms.filter(manager__isnull=True, status='active')
        elif filter_type == 'mine':
            chat_rooms = chat_rooms.filter(manager=request.user)
        elif filter_type == 'active':
            chat_rooms = chat_rooms.filter(status='active')
        elif filter_type == 'closed':
            chat_rooms = chat_rooms.filter(status='closed')
        elif filter_type != 'all':
            # Default to showing active and unassigned for staff
            chat_rooms = chat_rooms.filter(
                Q(manager=request.user) | Q(manager__isnull=True),
                status='active'
            )
        
        chat_rooms = chat_rooms.annotate(
            unread_count=Count('messages', filter=Q(messages__sender__isnull=False, messages__is_read=False))
        )
        template_name = 'chat/admin_chat_list_daisyui.html'
    else:
        # Customers see only their own chat rooms
        chat_rooms = ChatRoom.objects.filter(
            customer=request.user
        ).annotate(
            unread_count=Count('messages', filter=Q(messages__sender=F('manager'), messages__is_read=False))
        )
        template_name = 'chat/chat_list.html'
    
    # Order by updated_at to ensure consistent ordering
    chat_rooms = chat_rooms.order_by('-updated_at').distinct()
    
    # Pagination
    paginator = Paginator(chat_rooms, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Add statistics for staff users
    if request.user.is_staff:
        from datetime import date
        active_count = ChatRoom.objects.filter(status='active').count()
        unassigned_count = ChatRoom.objects.filter(manager__isnull=True, status='active').count()
        my_chats_count = ChatRoom.objects.filter(manager=request.user, status='active').count()
        total_unread = ChatMessage.objects.filter(is_read=False).exclude(sender=request.user).count()
        closed_today = ChatRoom.objects.filter(status='closed', updated_at__date=date.today()).count()
    else:
        active_count = unassigned_count = my_chats_count = total_unread = closed_today = 0
    
    context = {
        'chat_rooms': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'is_staff': request.user.is_staff,
        'active_count': active_count,
        'unassigned_count': unassigned_count,
        'my_chats_count': my_chats_count,
        'total_unread': total_unread,
        'closed_today': closed_today,
    }
    
    return render(request, template_name, context)


@login_required
def chat_room(request, pk):
    """View and participate in a specific chat room"""
    chat_room = get_object_or_404(ChatRoom, pk=pk)
    
    # Check permissions
    if not request.user.is_staff and chat_room.customer != request.user:
        messages.error(request, "You don't have permission to view this chat.")
        return redirect('chat:chat_list')
    
    if request.user.is_staff and chat_room.manager is None:
        # Auto-assign staff member to unassigned chat
        chat_room.manager = request.user
        chat_room.save()
        
        # Add system message
        ChatMessage.objects.create(
            chat_room=chat_room,
            message_type='system',
            content=f'{request.user.get_full_name()} has joined the chat.'
        )
    
    # Mark messages as read
    messages_to_read = chat_room.messages.exclude(sender=request.user).filter(is_read=False)
    for message in messages_to_read:
        message.mark_as_read()
    
    # Clear notifications
    ChatNotification.objects.filter(user=request.user, chat_room=chat_room).update(is_seen=True)
    
    # Handle message submission
    if request.method == 'POST':
        form = ChatMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.chat_room = chat_room
            message.sender = request.user
            
            # Set message type based on attachment
            if message.attachment:
                file_ext = message.attachment.name.lower()
                if any(file_ext.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
                    message.message_type = 'image'
                else:
                    message.message_type = 'file'
            
            message.save()
            
            # Create notification for the other party
            recipient = chat_room.customer if request.user.is_staff else chat_room.manager
            if recipient:
                ChatNotification.objects.create(
                    user=recipient,
                    chat_room=chat_room,
                    message=message
                )
            
            # AJAX response
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message_id': message.id,
                    'sender': message.sender.get_full_name(),
                    'content': message.content,
                    'created_at': message.created_at.strftime('%B %d, %Y at %I:%M %p'),
                    'is_sender': True
                })
            
            return redirect('chat:chat_room', pk=chat_room.pk)
    else:
        form = ChatMessageForm()
    
    # Get messages with pagination
    messages_list = chat_room.messages.select_related('sender')
    paginator = Paginator(messages_list, 50)
    page_number = request.GET.get('page')
    messages_page = paginator.get_page(page_number)
    
    # Calculate shop order count for the customer
    shop_order_count = 0
    if hasattr(chat_room.customer, 'invoices'):
        shop_order_count = chat_room.customer.invoices.filter(is_shop_order=True).count()
    
    context = {
        'chat_room': chat_room,
        'messages': messages_page,
        'form': form,
        'page_obj': messages_page,
        'is_staff': request.user.is_staff,
        'shop_order_count': shop_order_count,
    }
    
    # Use different template for admin users
    template_name = 'chat/admin_chat_room.html' if request.user.is_staff else 'chat/chat_room.html'
    
    return render(request, template_name, context)


@login_required
def create_chat(request):
    """Create a new chat room (for customers)"""
    if request.user.is_staff:
        messages.error(request, "Staff members cannot create new chats.")
        return redirect('chat:chat_list')
    
    if request.method == 'POST':
        form = ChatRoomForm(request.POST)
        if form.is_valid():
            chat_room = form.save(commit=False)
            chat_room.customer = request.user
            chat_room.save()
            
            # Create initial message
            initial_message = request.POST.get('initial_message', '')
            if initial_message:
                ChatMessage.objects.create(
                    chat_room=chat_room,
                    sender=request.user,
                    content=initial_message
                )
            
            messages.success(request, "Your chat has been created. A shop manager will respond soon.")
            return redirect('chat:chat_room', pk=chat_room.pk)
    else:
        form = ChatRoomForm()
    
    context = {
        'form': form
    }
    
    return render(request, 'chat/create_chat.html', context)


@login_required
def close_chat(request, pk):
    """Close a chat room"""
    chat_room = get_object_or_404(ChatRoom, pk=pk)
    
    # Check permissions
    if not request.user.is_staff and chat_room.customer != request.user:
        messages.error(request, "You don't have permission to close this chat.")
        return redirect('chat:chat_list')
    
    if request.method == 'POST':
        chat_room.status = 'closed'
        chat_room.save()
        
        # Add system message
        ChatMessage.objects.create(
            chat_room=chat_room,
            message_type='system',
            content=f'Chat closed by {request.user.get_full_name()}'
        )
        
        messages.success(request, "Chat has been closed.")
        return redirect('chat:chat_list')
    
    return render(request, 'chat/close_chat_confirm.html', {'chat_room': chat_room})


@login_required
def get_new_messages(request, pk):
    """AJAX endpoint to get new messages"""
    chat_room = get_object_or_404(ChatRoom, pk=pk)
    
    # Check permissions
    if not request.user.is_staff and chat_room.customer != request.user:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    last_message_id = request.GET.get('last_message_id', 0)
    
    new_messages = chat_room.messages.filter(
        id__gt=last_message_id
    ).exclude(
        sender=request.user
    ).select_related('sender')
    
    messages_data = []
    for message in new_messages:
        # Mark as read
        message.mark_as_read()
        
        messages_data.append({
            'id': message.id,
            'sender': message.sender.get_full_name() if message.sender else 'System',
            'sender_id': message.sender.id if message.sender else None,
            'content': message.content,
            'created_at': message.created_at.strftime('%B %d, %Y at %I:%M %p'),
            'message_type': message.message_type,
            'is_sender': False
        })
    
    return JsonResponse({
        'messages': messages_data,
        'count': len(messages_data)
    })


@login_required
def get_unread_count(request):
    """AJAX endpoint to get total unread message count"""
    if request.user.is_staff:
        unread_count = ChatMessage.objects.filter(
            chat_room__manager=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
    else:
        unread_count = ChatMessage.objects.filter(
            chat_room__customer=request.user,
            is_read=False
        ).exclude(sender=request.user).count()
    
    return JsonResponse({'unread_count': unread_count})