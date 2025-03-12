import logging
from django.views import View
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Concept, Relation
import math
import time
import traceback

logger = logging.getLogger(__name__)

class ConceptMapView(View):
    template_name = 'concept_builder/concept_map.html'

    def get_context_data(self):
        request_id = time.time()
        #logger.debug(f"[{request_id}] Entering get_context_data, call stack: {''.join(traceback.format_stack())}")
        concepts = Concept.objects.all()
        relations = Relation.objects.all()
        central_node = None
        if concepts.exists():
            central_node = concepts.first()

        if concepts.count() > 1:
            radius = 150
            angle_step = 2 * math.pi / (concepts.count() - 1)
            for idx, concept in enumerate(concepts):
                if concept.id == central_node.id:
                    concept.x_pos = 0
                    concept.y_pos = 0
                elif concept.x_pos == 0 and concept.y_pos == 0:
                    angle = idx * angle_step if idx > 0 else 0
                    concept.x_pos = radius * math.cos(angle)
                    concept.y_pos = radius * math.sin(angle)
                    concept.save()
        elif central_node and central_node.x_pos == 0 and central_node.y_pos == 0:
                central_node.x_pos = 0
                central_node.y_pos = 0
                central_node.save()

        positions = {c.id: {'x': c.x_pos, 'y': c.y_pos} for c in concepts}
        logger.debug(f"[{request_id}] Context data - concepts: {len(concepts)}, relations: {len(relations)}")
        return {
            'concepts': concepts,
            'relations': relations,
            'central_node': central_node,
            'positions': positions
        }

    def get(self, request):
        request_id = time.time()
        logger.debug(f"[{request_id}] Entering get method")
        context = self.get_context_data()  # Call once and store
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action')
        if action == 'add_concept':
            return self.add_concept(request)
        elif action == 'add_relation':
            return self.add_relation(request)
        elif action == 'update_position':
            return self.update_position(request)
        elif action == 'delete_concept':
            return self.delete_concept(request)
        elif action == 'create_central_node':
            return self.create_central_node(request)
        elif action == 'delete_central_node':
            return self.delete_central_node(request)
        return redirect('concept_map')

    def add_concept(self, request):
        request_id = time.time()
        logger.debug(f"[{request_id}] Creating new concept")
        
        name = request.POST.get('name')
        
        # Get current context without auto-creating central node
        context = self.get_context_data()
        central_node = context.get('central_node')
        
        # Make this concept the central node if none exists
        make_central = central_node is None
        
        if name and (not central_node or name != central_node.name):
            x_pos = float(request.POST.get('x_pos', 100 * (Concept.objects.count() % 5)))
            y_pos = float(request.POST.get('y_pos', 100 * (Concept.objects.count() // 5)))
            
            # If this should be central node, position at center
            if make_central:
                x_pos = 0
                y_pos = 0
                
            concept = Concept.objects.create(name=name, x_pos=x_pos, y_pos=y_pos)
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'node_id': concept.id,
                    'name': concept.name,
                    'x_pos': concept.x_pos,
                    'y_pos': concept.y_pos,
                    'is_central': make_central
                })
        return redirect('concept_map')

    def add_relation(self, request):
        source_id = request.POST.get('source')
        target_id = request.POST.get('target')
        request_id = time.time()
        logger.debug(f"[{request_id}] Received add_relation request: source={source_id}, target={target_id}")
        if source_id and target_id and source_id != target_id:
            # Check for existing relation
            if Relation.objects.filter(source_id=source_id, target_id=target_id).exists():
                logger.debug(f"[{request_id}] Relation already exists: {source_id} -> {target_id}")
                return JsonResponse({'status': 'error', 'message': 'Relation already exists'}, status=400)
            Relation.objects.create(source_id=source_id, target_id=target_id)
            logger.debug(f"[{request_id}] Relation created: {source_id} -> {target_id}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'source_id': source_id,
                    'target_id': target_id
                })
        else:
            logger.error(f"[{request_id}] Failed to create relation: source={source_id}, target={target_id}")
            return JsonResponse({'status': 'error', 'message': 'Invalid source or target'}, status=400)
        return redirect('concept_map')

    def update_position(self, request):
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            node_id = request.POST.get('node_id')
            x_pos = request.POST.get('x_pos')
            y_pos = request.POST.get('y_pos')
            request_id = time.time()
            logger.debug(f"[{request_id}] Updating position for node {node_id}: x={x_pos}, y={y_pos}")
            try:
                concept = Concept.objects.get(id=node_id)
                concept.x_pos = float(x_pos)
                concept.y_pos = float(y_pos)
                concept.save()
                logger.debug(f"[{request_id}] Position updated for node {node_id}: x={concept.x_pos}, y={concept.y_pos}")
                return JsonResponse({'status': 'success'})
            except Concept.DoesNotExist:
                logger.error(f"[{request_id}] Node {node_id} not found")
                return JsonResponse({'status': 'error', 'message': 'Node not found'}, status=404)
            except ValueError as e:
                logger.error(f"[{request_id}] Invalid position values: x={x_pos}, y={y_pos}, error={str(e)}")
                return JsonResponse({'status': 'error', 'message': 'Invalid position values'}, status=400)
        logger.error(f"[{request_id}] Invalid request for update_position")
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    def delete_concept(self, request):
        concept_id = request.POST.get('concept_id')
        central_node = self.get_context_data()['central_node']
        request_id = time.time()
        
        logger.debug(f"[{request_id}] Deleting concept {concept_id}")
        
        # Check if concept exists and is not the central node
        if concept_id and concept_id != str(central_node.id):
            try:
                # Delete related relations first
                Relation.objects.filter(source_id=concept_id).delete()
                Relation.objects.filter(target_id=concept_id).delete()
                # Then delete the concept
                Concept.objects.filter(id=concept_id).delete()
                logger.debug(f"[{request_id}] Successfully deleted concept {concept_id}")
                
                # Return JSON response for AJAX requests
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'node_id': concept_id
                    })
            except Exception as e:
                logger.error(f"[{request_id}] Error deleting concept {concept_id}: {str(e)}")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'error',
                        'message': str(e)
                    }, status=500)
        else:
            logger.error(f"[{request_id}] Cannot delete central node or invalid concept ID: {concept_id}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Cannot delete the central node'
                }, status=400)
                
        return redirect('concept_map')

    def create_central_node(self, request):
        """Function to create a new central node after the previous one was deleted"""
        name = request.POST.get('name')
        request_id = time.time()
        
        logger.debug(f"[{request_id}] Creating new central node with name: {name}")
        
        try:
            # Create a new central node at the center of the map
            new_central_node = Concept.objects.create(
                name=name, 
                x_pos=0,
                y_pos=0
            )
            
            logger.debug(f"[{request_id}] Successfully created new central node {new_central_node.id}")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'node_id': new_central_node.id,
                    'name': new_central_node.name,
                    'x_pos': new_central_node.x_pos,
                    'y_pos': new_central_node.y_pos
                })
        except Exception as e:
            logger.error(f"[{request_id}] Error creating new central node: {str(e)}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
        
        return redirect('concept_map')

    def delete_central_node(self, request):
        """Special function to delete the central node and reset the concept map"""
        request_id = time.time()
        
        logger.debug(f"[{request_id}] Deleting all concepts and relations")
        
        try:
            # Delete all relations first
            Relation.objects.all().delete()
            
            # Delete all concepts
            Concept.objects.all().delete()
            
            logger.debug(f"[{request_id}] Successfully reset concept map")
            
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Concept map has been reset'
                })
        except Exception as e:
            logger.error(f"[{request_id}] Error deleting concepts: {str(e)}")
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'error',
                    'message': str(e)
                }, status=500)
        
        return redirect('concept_map')
