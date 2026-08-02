
// FLUTTER - Panel Empleado ve historial evaluaciones

Future<List> getMisEvaluaciones() async {
  final res = await dio.get('/api/empleado/mis_evaluaciones', options: Options(headers: {'X-User':'empleado_1'}));
  return res.data;
}

// Widget
ListView.builder(
  itemCount: evaluaciones.length,
  itemBuilder: (c,i){
    final ev = evaluaciones[i];
    return Card(
      child: ListTile(
        title: Text("Evaluación ${ev['fecha']} - Promedio ${ev['promedio']}"),
        subtitle: Text(ev['comentario_general'] ?? ''),
        trailing: Icon(Icons.star, color: Colors.amber),
        onTap: ()=> Navigator.push(... detalle ...)
      )
    );
  }
)
