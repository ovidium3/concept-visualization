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
        central_node = Concept.objects.filter(name="Climate Change").first()
        if not central_node:
            central_node = Concept.objects.create(name="Climate Change", x_pos=0, y_pos=0)

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
        else:
            if central_node.x_pos == 0 and central_node.y_pos == 0:
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
        return redirect('concept_map')

    def add_concept(self, request):
        name = request.POST.get('name')
        central_node = self.get_context_data()['central_node']
        if name and name != central_node.name:
            x_pos = float(request.POST.get('x_pos', 100 * (Concept.objects.count() % 5)))
            y_pos = float(request.POST.get('y_pos', 100 * (Concept.objects.count() // 5)))
            concept = Concept.objects.create(name=name, x_pos=x_pos, y_pos=y_pos)
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'node_id': concept.id,
                    'name': concept.name,
                    'x_pos': concept.x_pos,
                    'y_pos': concept.y_pos
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
        if concept_id and concept_id != str(central_node.id):
            Concept.objects.filter(id=concept_id).delete()
        return redirect('concept_map')